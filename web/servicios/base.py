import logging

import requests
from django.conf import settings
from django.utils import translation
from django.utils.translation import gettext as _

logger = logging.getLogger(__name__)


class ErrorMicroservicio(Exception):
    """El microservicio respondió con un error de negocio (4xx)."""

    def __init__(self, status, detalle, campos=None, codigo=""):
        super().__init__(detalle)
        self.status = status
        self.detalle = detalle
        self.campos = campos or {}
        self.codigo = codigo


class MicroservicioNoDisponible(ErrorMicroservicio):
    """No hubo respuesta del microservicio o respondió 5xx."""

    def __init__(self, servicio, detalle=None):
        super().__init__(503, detalle or _("El servicio de %(servicio)s no está disponible en este momento.") % {"servicio": servicio})
        self.servicio = servicio


class ClienteMicroservicio:
    """Cliente base: timeout, token interno, usuario e idioma en cada petición."""

    nombre = ""          # clave en settings.MICROSERVICIOS
    nombre_visible = ""  # nombre traducible para los mensajes de error
    prefijo = ""

    def __init__(self, usuario_id=None):
        self.base_url = settings.MICROSERVICIOS[self.nombre].rstrip("/")
        self.usuario_id = usuario_id

    def _headers(self):
        headers = {
            "X-Service-Token": settings.SERVICE_TOKEN,
            "Accept-Language": translation.get_language() or settings.LANGUAGE_CODE,
        }
        if self.usuario_id is not None:
            headers["X-Usuario-Id"] = str(self.usuario_id)
        return headers

    def _peticion(self, metodo, ruta, esperado=(200,), **kwargs):
        url = f"{self.base_url}{self.prefijo}{ruta}"
        try:
            resp = requests.request(
                metodo, url, headers=self._headers(), timeout=settings.MICROSERVICIOS_TIMEOUT, **kwargs
            )
        except requests.RequestException as exc:
            logger.warning("Microservicio %s sin respuesta (%s): %s", self.nombre, url, exc)
            raise MicroservicioNoDisponible(str(self.nombre_visible))

        if resp.status_code in esperado:
            return resp.json()

        try:
            cuerpo = resp.json()
        except ValueError:
            cuerpo = {}
        if resp.status_code >= 500:
            logger.warning("Microservicio %s respondió %s: %s", self.nombre, resp.status_code, cuerpo)
            raise MicroservicioNoDisponible(str(self.nombre_visible), cuerpo.get("detalle"))
        raise ErrorMicroservicio(
            resp.status_code,
            cuerpo.get("detalle", _("Error inesperado.")),
            cuerpo.get("campos"),
            cuerpo.get("error", ""),
        )
