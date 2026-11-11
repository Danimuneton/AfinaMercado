"""
Clientes HTTP hacia los otros microservicios y publicador de eventos
asíncronos (Celery + Redis).
"""
import logging

import requests
from celery import Celery
from flask import current_app
from flask_babel import gettext as _

from comun import ErrorServicio, seleccionar_idioma

logger = logging.getLogger(__name__)

TIMEOUT = 8


class ServicioNoDisponible(ErrorServicio):
    def __init__(self, detalle):
        super().__init__(503, "servicio_no_disponible", detalle)


def _headers(usuario_id=None):
    headers = {
        "X-Service-Token": current_app.config["SERVICE_TOKEN"],
        "Accept-Language": seleccionar_idioma(),
    }
    if usuario_id is not None:
        headers["X-Usuario-Id"] = str(usuario_id)
    return headers


def _llamar(metodo, url, nombre_servicio, **kwargs):
    try:
        resp = requests.request(metodo, url, timeout=TIMEOUT, **kwargs)
    except requests.RequestException:
        raise ServicioNoDisponible(
            _("El servicio de %(servicio)s no está disponible.", servicio=nombre_servicio)
        )
    if resp.status_code >= 500:
        raise ServicioNoDisponible(
            _("El servicio de %(servicio)s no está disponible.", servicio=nombre_servicio)
        )
    return resp


def _propagar_error(resp):
    """Re-lanza un error 4xx de otro servicio conservando su mensaje."""
    try:
        cuerpo = resp.json()
    except ValueError:
        cuerpo = {}
    raise ErrorServicio(
        resp.status_code,
        cuerpo.get("error", "error_dependencia"),
        cuerpo.get("detalle", _("Error en un servicio dependiente.")),
    )


class CarritoClient:
    def _url(self, ruta):
        return f"{current_app.config['CARRITO_URL']}/api/v2/carrito{ruta}"

    def ver(self, usuario_id):
        resp = _llamar("GET", self._url("/"), _("carrito"), headers=_headers(usuario_id))
        if resp.status_code != 200:
            _propagar_error(resp)
        return resp.json()

    def vaciar(self, usuario_id):
        _llamar("DELETE", self._url("/"), _("carrito"), headers=_headers(usuario_id))


class CatalogoClient:
    def _url(self, ruta):
        return f"{current_app.config['CATALOGO_URL']}/api/v2/catalogo/instrumentos{ruta}"

    def reservar(self, ids):
        resp = _llamar("POST", self._url("/reservar"), _("catálogo"), json={"ids": ids}, headers=_headers())
        if resp.status_code != 200:
            _propagar_error(resp)
        return resp.json()

    def liberar(self, ids):
        """Compensación (best-effort): si falla solo se registra en el log."""
        try:
            _llamar("POST", self._url("/liberar"), _("catálogo"), json={"ids": ids}, headers=_headers())
        except ErrorServicio:
            logger.error("No se pudieron liberar los instrumentos %s", ids)


class PagoClient:
    def procesar(self, orden_id, monto, metodo):
        url = f"{current_app.config['PAGO_URL']}/api/v2/pagos/"
        payload = {"orden_id": orden_id, "monto": float(monto), "metodo": metodo}
        resp = _llamar("POST", url, _("pagos"), json=payload, headers=_headers())
        if resp.status_code != 201:
            _propagar_error(resp)
        return resp.json()


class PublicadorEventos:
    """Envía tareas al worker de notificaciones a través de Redis (Celery)."""

    _celery = None

    @classmethod
    def _app(cls):
        broker = current_app.config.get("CELERY_BROKER_URL")
        if not broker:
            return None
        if cls._celery is None:
            cls._celery = Celery("ordenes_service", broker=broker)
            # Fallar rápido si Redis está caído: la compra no puede quedarse esperando al broker.
            cls._celery.conf.update(
                broker_connection_timeout=2,
                broker_connection_retry_on_startup=False,
                broker_transport_options={
                    "max_retries": 1,
                    "interval_start": 0,
                    "interval_step": 0.5,
                    "interval_max": 0.5,
                },
                redis_socket_connect_timeout=2,
                redis_socket_timeout=2,
            )
        return cls._celery

    @classmethod
    def orden_confirmada(cls, orden, email, idioma):
        app = cls._app()
        if app is None:
            logger.info("Broker no configurado; no se envía notificación")
            return False
        try:
            app.send_task(
                "notificaciones.enviar_confirmacion_orden",
                kwargs={"orden": orden, "email": email, "idioma": idioma},
                retry=False,
            )
            return True
        except Exception:  # El broker caído no debe tumbar la compra.
            logger.exception("No se pudo publicar el evento de orden confirmada")
            return False
