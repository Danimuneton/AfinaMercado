from django.db import transaction

from .domain.orden_builder import OrdenBuilder
from .infra.notificador_factory import NotificadorFactory
from .models import Orden, LineaOrden, Pago, Envio


class OrdenService:
    def __init__(self):
        self.notificador = NotificadorFactory.crear()

    @transaction.atomic
    def crear_orden_desde_carrito(self, comprador, carrito, direccion_envio):
        orden_data = (
            OrdenBuilder()
            .para_comprador(comprador)
            .con_lineas(carrito.items.select_related("instrumento").all())
            .con_envio(direccion_envio)
            .build()
        )

        orden = Orden.objects.create(
            comprador=comprador,
            total=orden_data["total"],
            direccion_envio=direccion_envio,
        )

        for linea in orden_data["lineas"]:
            LineaOrden.objects.create(
                orden=orden,
                instrumento=linea["instrumento"],
                precio_final=linea["precio_final"],
            )

        for instrumento in orden_data["instrumentos_a_marcar"]:
            instrumento.estado_venta = "vendido"
            instrumento.save(update_fields=["estado_venta"])

        Pago.objects.create(orden=orden, monto=orden_data["total"])
        Envio.objects.create(orden=orden, direccion=direccion_envio)

        carrito.items.all().delete()

        self.notificador.enviar_confirmacion({**orden_data, "orden_id": orden.id})

        return orden