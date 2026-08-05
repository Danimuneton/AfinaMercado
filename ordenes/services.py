from .domain.orden_builder import OrdenBuilder
from .infra.notificador_factory import NotificadorFactory
from .models import Orden


class OrdenService:
    def __init__(self):
        self.notificador = NotificadorFactory.crear()  # Inyección de dependencias

    def crear_orden_desde_carrito(self, comprador, carrito, direccion_envio, garantia_datos=None):
        builder = OrdenBuilder().para_comprador(comprador).con_lineas(carrito.items.all())

        if garantia_datos:
            builder = builder.con_garantia(**garantia_datos)

        orden_data = builder.con_envio(direccion_envio).build()

        orden = Orden.objects.create(
            comprador=comprador,
            total=orden_data["total"],
            direccion_envio=direccion_envio,
        )

        self.notificador.enviar_confirmacion(orden_data)

        return orden