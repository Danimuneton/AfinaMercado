class OrdenInvalidaError(Exception):
    """Se lanza cuando la orden no cumple las reglas de negocio."""
    pass


class OrdenBuilder:
    """
    Construye una Orden paso a paso (Fluent Interface).
    No guarda nada en la base de datos: solo valida y arma los datos.
    El .build() falla si algo obligatorio falta o es inválido.
    """

    def __init__(self):
        self._comprador = None
        self._lineas = []
        self._garantia = None
        self._envio_direccion = None

    def para_comprador(self, comprador):
        self._comprador = comprador
        return self  # permite encadenar métodos: builder.para_comprador(x).con_lineas(y)...

    def con_lineas(self, items_carrito):
        for item in items_carrito:
            instrumento = item.instrumento
            if instrumento.estado_venta == "vendido":
                raise OrdenInvalidaError(
                    f"El instrumento {instrumento.marca} {instrumento.modelo} ya fue vendido."
                )
            self._lineas.append({
                "instrumento": instrumento,
                "precio_final": instrumento.precio_base,
            })
        return self

    def con_garantia(self, duracion_meses=None, costo=None):
        if duracion_meses:
            self._garantia = {"duracion_meses": duracion_meses, "costo": costo}
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
        if self._garantia:
            total += self._garantia["costo"]

        return {
            "comprador": self._comprador,
            "lineas": self._lineas,
            "garantia": self._garantia,
            "envio_direccion": self._envio_direccion,
            "total": total,
        }