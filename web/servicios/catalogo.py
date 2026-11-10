from django.utils.translation import gettext_lazy as _

from .base import ClienteMicroservicio


class CatalogoServicio(ClienteMicroservicio):
    nombre = "catalogo"
    nombre_visible = _("catálogo")
    prefijo = "/api/v2/catalogo"

    def categorias(self):
        return self._peticion("GET", "/categorias")

    def instrumentos(self, texto="", categoria_id=None, vendedor_usuario_id=None, estado="disponible"):
        params = {"estado": estado}
        if texto:
            params["q"] = texto
        if categoria_id:
            params["categoria_id"] = categoria_id
        if vendedor_usuario_id:
            params["vendedor_usuario_id"] = vendedor_usuario_id
        return self._peticion("GET", "/instrumentos", params=params)

    def instrumento(self, instrumento_id):
        return self._peticion("GET", f"/instrumentos/{instrumento_id}")

    def sincronizar_vendedor(self, usuario_id, nombre, contacto):
        return self._peticion(
            "POST",
            "/vendedores/sincronizar",
            esperado=(200, 201),
            json={"usuario_id": usuario_id, "nombre": nombre, "contacto": contacto},
        )

    def publicar_instrumento(self, datos):
        return self._peticion("POST", "/instrumentos", esperado=(201,), json=datos)
