"""
Worker asíncrono (Celery + Redis) - AfinaMercado.

Consume tareas de la cola de Redis para que los procesos de fondo no
bloqueen a Django ni a los microservicios:
  - notificaciones.enviar_confirmacion_orden: avisa al comprador (Factory).
  - reportes.generar_reporte_ventas: calcula el reporte de ventas.
"""
import logging
import os
from collections import defaultdict
from datetime import datetime, timezone

import requests
from babel.support import Translations
from celery import Celery

from notificadores import NotificadorFactory

logger = logging.getLogger(__name__)

BROKER = os.environ.get("CELERY_BROKER_URL", "redis://redis:6379/0")
BACKEND = os.environ.get("CELERY_RESULT_BACKEND", "redis://redis:6379/1")
ORDENES_URL = os.environ.get("ORDENES_URL", "http://flask_ordenes_service:5000").rstrip("/")
SERVICE_TOKEN = os.environ.get("SERVICE_TOKEN", "")
DIRECTORIO_TRADUCCIONES = os.path.join(os.path.dirname(__file__), "translations")

app = Celery("notificaciones_service", broker=BROKER, backend=BACKEND)
app.conf.update(
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    result_expires=3600,
    task_acks_late=True,
    worker_prefetch_multiplier=1,
    broker_connection_retry_on_startup=True,
    timezone="UTC",
)


def _traductor(idioma):
    """gettext con los catálogos .mo del worker (es / en)."""
    idioma = idioma if idioma in ("es", "en") else "es"
    return Translations.load(DIRECTORIO_TRADUCCIONES, [idioma]).gettext


def _formato_cop(valor):
    return f"${valor:,.0f} COP".replace(",", ".")


@app.task(
    name="notificaciones.enviar_confirmacion_orden",
    autoretry_for=(OSError,),
    retry_backoff=True,
    max_retries=3,
)
def enviar_confirmacion_orden(orden, email="", idioma="es"):
    _ = _traductor(idioma)
    estados = {"creada": _("Creada"), "pagada": _("Pagada"), "cancelada": _("Cancelada")}
    estado = estados.get(orden.get("estado"), orden.get("estado", ""))
    asunto = _("AfinaMercado: confirmación de tu orden #%(id)s") % {"id": orden["id"]}
    lineas = "\n".join(
        f"  - {l['instrumento']}: {_formato_cop(l['precio_final'])}" for l in orden.get("lineas", [])
    )
    cuerpo = "\n".join(
        [
            _("¡Gracias por tu compra!"),
            "",
            _("Orden: #%(id)s") % {"id": orden["id"]},
            _("Estado: %(estado)s") % {"estado": estado},
            _("Instrumentos:"),
            lineas,
            _("Total: %(total)s") % {"total": _formato_cop(orden["total"])},
            _("Dirección de envío: %(direccion)s") % {"direccion": orden.get("direccion_envio", "")},
        ]
    )
    canal = NotificadorFactory.crear().enviar(email, asunto, cuerpo)
    return {"orden_id": orden["id"], "canal": canal, "enviado_en": datetime.now(timezone.utc).isoformat()}


@app.task(
    name="reportes.generar_reporte_ventas",
    autoretry_for=(requests.RequestException,),
    retry_backoff=True,
    max_retries=3,
)
def generar_reporte_ventas(idioma="es"):
    resp = requests.get(
        f"{ORDENES_URL}/api/v2/ordenes/internos/ventas",
        headers={"X-Service-Token": SERVICE_TOKEN, "Accept-Language": idioma},
        timeout=15,
    )
    resp.raise_for_status()
    ventas = resp.json()

    por_categoria = defaultdict(lambda: {"unidades": 0, "ingresos": 0.0})
    por_metodo = defaultdict(lambda: {"ordenes": 0, "ingresos": 0.0})
    for orden in ventas:
        por_metodo[orden["metodo_pago"]]["ordenes"] += 1
        por_metodo[orden["metodo_pago"]]["ingresos"] += orden["total"]
        for linea in orden["lineas"]:
            por_categoria[linea["categoria"]]["unidades"] += 1
            por_categoria[linea["categoria"]]["ingresos"] += linea["precio_final"]

    ingresos = sum(o["total"] for o in ventas)
    return {
        "generado_en": datetime.now(timezone.utc).isoformat(),
        "total_ordenes": len(ventas),
        "ingresos_totales": ingresos,
        "ticket_promedio": ingresos / len(ventas) if ventas else 0.0,
        "por_categoria": sorted(
            ({"categoria": k, **v} for k, v in por_categoria.items()),
            key=lambda x: x["ingresos"],
            reverse=True,
        ),
        "por_metodo": sorted(
            ({"metodo": k, **v} for k, v in por_metodo.items()),
            key=lambda x: x["ingresos"],
            reverse=True,
        ),
    }
