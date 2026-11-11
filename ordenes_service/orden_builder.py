"""
Patrón Builder (migrado desde el monolito). Arma y valida los datos de una
orden sin tocar la base de datos.
"""
from decimal import Decimal

from flask_babel import gettext as _

from comun import solicitud_invalida
from models import METODOS_PAGO


class OrdenBuilder:
    def __init__(self, umbral_seguro=Decimal("5000000")):
        self._usuario_id = None
        self._email = ""
        self._lineas = []
        self._direccion = None
        self._metodo_pago = None
        self._umbral_seguro = umbral_seguro

    def para_usuario(self, usuario_id, email=""):
        self._usuario_id = usuario_id
        self._email = email or ""
        return self

    def con_lineas(self, instrumentos):
        """Recibe los instrumentos ya reservados por el microservicio de Catálogo."""
        for instrumento in instrumentos:
            self._lineas.append(
                {
                    "instrumento_id": instrumento["id"],
                    "marca": instrumento["marca"],
                    "modelo": instrumento["modelo"],
                    "categoria": instrumento["categoria"]["nombre"],
                    "vendedor": instrumento["vendedor"]["nombre"],
                    "precio_final": Decimal(str(instrumento["precio_base"])),
                }
            )
        return self

    def con_envio(self, direccion):
        self._direccion = (direccion or "").strip()
        return self

    def con_metodo_pago(self, metodo):
        self._metodo_pago = metodo
        return self

    def build(self):
        if not self._usuario_id:
            raise solicitud_invalida(_("La orden necesita un comprador."))
        if not self._lineas:
            raise solicitud_invalida(_("La orden necesita al menos una línea de compra."))
        if not self._direccion:
            raise solicitud_invalida(_("La orden necesita una dirección de envío."))
        if self._metodo_pago not in METODOS_PAGO:
            raise solicitud_invalida(_("Método de pago no válido."))

        total = sum((l["precio_final"] for l in self._lineas), Decimal("0"))
        return {
            "usuario_id": self._usuario_id,
            "email": self._email,
            "lineas": self._lineas,
            "direccion_envio": self._direccion,
            "metodo_pago": self._metodo_pago,
            "total": total,
            # Regla de negocio: los envíos de alto valor van asegurados.
            "envio_asegurado": total >= self._umbral_seguro,
        }
