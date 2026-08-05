import os


class NotificadorConsola:
    """Para desarrollo: solo imprime en la consola, no manda nada real."""
    def enviar_confirmacion(self, orden_data):
        print(f"[DEV] Orden confirmada para {orden_data['comprador']}. Total: {orden_data['total']}")


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