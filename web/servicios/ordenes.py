from django.utils.translation import gettext_lazy as _

from .base import ClienteMicroservicio


class OrdenesServicio(ClienteMicroservicio):
    nombre = "ordenes"
    nombre_visible = _("órdenes")
    prefijo = "/api/v2/ordenes"

    def crear(self, direccion_envio, metodo_pago, email=""):
        return self._peticion(
            "POST",
            "/",
            esperado=(201,),
            json={"direccion_envio": direccion_envio, "metodo_pago": metodo_pago, "email": email},
        )

    def listar(self):
        return self._peticion("GET", "/")

    def detalle(self, orden_id):
        return self._peticion("GET", f"/{orden_id}")
