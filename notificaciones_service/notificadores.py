"""
Patrón Factory (migrado desde el monolito): decide qué canal de
notificación usar según el entorno. El resto del código solo pide un
notificador y no sabe si se imprime en consola o se envía un correo real.
"""
import logging
import os
import smtplib
from email.message import EmailMessage

logger = logging.getLogger(__name__)


class NotificadorConsola:
    """Desarrollo / demo: escribe el mensaje en el log del worker."""

    def enviar(self, destinatario, asunto, cuerpo):
        logger.info("[NOTIFICACION] Para: %s | %s\n%s", destinatario or "-", asunto, cuerpo)
        return "consola"


class NotificadorEmailSMTP:
    """Producción: envía el correo por SMTP (credenciales en variables de entorno)."""

    def __init__(self):
        self.host = os.environ["SMTP_HOST"]
        self.port = int(os.environ.get("SMTP_PORT", "587"))
        self.usuario = os.environ.get("SMTP_USER", "")
        self.clave = os.environ.get("SMTP_PASSWORD", "")
        self.remitente = os.environ.get("SMTP_FROM", self.usuario)

    def enviar(self, destinatario, asunto, cuerpo):
        if not destinatario:
            return NotificadorConsola().enviar(destinatario, asunto, cuerpo)
        mensaje = EmailMessage()
        mensaje["From"] = self.remitente
        mensaje["To"] = destinatario
        mensaje["Subject"] = asunto
        mensaje.set_content(cuerpo)
        with smtplib.SMTP(self.host, self.port, timeout=15) as smtp:
            smtp.starttls()
            if self.usuario:
                smtp.login(self.usuario, self.clave)
            smtp.send_message(mensaje)
        return "email"


class NotificadorFactory:
    @staticmethod
    def crear():
        if os.environ.get("ENV_TYPE", "DEV") == "PROD" and os.environ.get("SMTP_HOST"):
            return NotificadorEmailSMTP()
        return NotificadorConsola()
