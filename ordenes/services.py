import logging

from django.db import transaction

from .domain.orden_builder import OrdenBuilder
from .infra.notificador_factory import NotificadorFactory
from .infra.pago_client import PagoClient, PagoServiceError
from .models import Orden, LineaOrden, Pago, Envio

logger = logging.getLogger(__name__)


class OrdenService:
    def __init__(self):
        self.notificador = NotificadorFactory.crear()
        self.pago_client = PagoClient()

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

        # --- Strangler Pattern ---
        # El pago YA NO se procesa dentro del monolito: se delega al
        # microservicio Flask a través del cliente HTTP. De forma resiliente:
        # si el servicio no responde, la orden queda registrada y el pago
        # pendiente, en lugar de tumbar todo el flujo.
        try:
            resultado_pago = self.pago_client.procesar_pago(
                orden_id=orden.id,
                monto=orden_data["total"],
                metodo="tarjeta",
            )
            Pago.objects.create(orden=orden, monto=orden_data["total"])
            orden.estado = "pagada"
            orden.save(update_fields=["estado"])
            logger.info(
                "Pago aprobado por microservicio: %s",
                resultado_pago.get("transaccion_id"),
            )
        except PagoServiceError as exc:
            logger.warning("Pago no procesado por el microservicio: %s", exc)

        Envio.objects.create(orden=orden, direccion=direccion_envio)

        carrito.items.all().delete()

        self.notificador.enviar_confirmacion({**orden_data, "orden_id": orden.id})

        return orden
