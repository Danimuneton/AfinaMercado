from django.utils.translation import gettext_lazy as _

from .base import ClienteMicroservicio


class CarritoServicio(ClienteMicroservicio):
    nombre = "carrito"
    nombre_visible = _("carrito")
    prefijo = "/api/v2/carrito"

    def ver(self):
        return self._peticion("GET", "/")

    def agregar(self, instrumento_id):
        return self._peticion("POST", "/items", esperado=(201,), json={"instrumento_id": instrumento_id})

    def quitar(self, instrumento_id):
        return self._peticion("DELETE", f"/items/{instrumento_id}")
