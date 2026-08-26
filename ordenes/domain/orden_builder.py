class OrdenInvalidaError(Exception):
    """Datos incompletos o inválidos para crear la orden (HTTP 400)."""
    pass


class InstrumentoNoDisponibleError(Exception):
    """El instrumento ya fue vendido o no está disponible (HTTP 409)."""
    pass


class OrdenBuilder:
    """
    Construye una Orden paso a paso (Fluent Interface).
    No guarda nada en la base de datos: solo valida y arma los datos.
    """

    def __init__(self):
        self._comprador = None
        self._lineas = []
        self._instrumentos_a_marcar = []
        self._envio_direccion = None

    def para_comprador(self, comprador):
        self._comprador = comprador
        return self

    def con_lineas(self, items_carrito):
        for item in items_carrito:
            instrumento = item.instrumento
            if instrumento.estado_venta == "vendido":
                raise InstrumentoNoDisponibleError(
                    f"El instrumento {instrumento.marca} {instrumento.modelo} ya no está disponible."
                )
            self._lineas.append({"instrumento": instrumento, "precio_final": instrumento.precio_base})
            self._instrumentos_a_marcar.append(instrumento)
        return self

    def con_envio(self, direccion):
        self._envio_direccion = direccion
        return self

    def build(self):
        if not self._comprador:
            raise OrdenInvalidaError("La orden necesita un comprador.")
        if not self._lineas:
            raise OrdenInvalidaError("La orden necesita al menos una línea de compra.")
        if not self._envio_direccion:
            raise OrdenInvalidaError("La orden necesita una dirección de envío.")

        total = sum(l["precio_final"] for l in self._lineas)

        return {
            "comprador": self._comprador,
            "lineas": self._lineas,
            "envio_direccion": self._envio_direccion,
            "total": total,
            "instrumentos_a_marcar": self._instrumentos_a_marcar,
        }