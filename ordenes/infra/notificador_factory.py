import logging
import os

logger = logging.getLogger(__name__)


class NotificadorConsola:
    """Para desarrollo: solo escribe en el log, no manda nada real."""
    def enviar_confirmacion(self, orden_data):
        logger.info("[DEV] Orden confirmada para %s. Total: %s", orden_data["comprador"], orden_data["total"])


class NotificadorEmailReal:
    """Para producción: aquí iría la integración real (ej. SendGrid, Gmail API, etc)."""
    def enviar_confirmacion(self, orden_data):
        # TODO: integrar con un servicio real de correo
        pass


class NotificadorFactory:
    """
    Decide qué notificador usar según la variable de entorno ENV_TYPE.
    El resto del código no necesita saber si estamos en DEV o PROD,
    solo le pide un notificador a esta Factory.
    """
    @staticmethod
    def crear():
        tipo = os.environ.get("ENV_TYPE", "DEV")
        if tipo == "PROD":
            return NotificadorEmailReal()
        return NotificadorConsola()