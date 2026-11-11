"""
Etiquetas traducibles para los códigos que devuelven los microservicios
(los servicios responden códigos estables como "pagada"; la interfaz los
muestra en el idioma del usuario).
"""
from django.utils.translation import gettext_lazy as _

CONDICIONES = {
    "excelente": _("Excelente"),
    "bueno": _("Bueno"),
    "regular": _("Regular"),
}

ESTADOS_VENTA = {
    "disponible": _("Disponible"),
    "vendido": _("Vendido"),
}

ESTADOS_ORDEN = {
    "creada": _("Creada"),
    "pagada": _("Pagada"),
    "cancelada": _("Cancelada"),
}

ESTADOS_ENVIO = {
    "pendiente": _("Pendiente"),
    "en_camino": _("En camino"),
    "entregado": _("Entregado"),
}

METODOS_PAGO = {
    "tarjeta": _("Tarjeta de crédito/débito"),
    "transferencia": _("Transferencia bancaria"),
    "pse": _("PSE"),
    "nequi": _("Nequi"),
}

TODAS = {**CONDICIONES, **ESTADOS_VENTA, **ESTADOS_ORDEN, **ESTADOS_ENVIO, **METODOS_PAGO}
