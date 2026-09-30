from rest_framework import serializers
from .models import (
    Vendedor,
    Categoria,
    Instrumento,
    Carrito,
    ItemCarrito,
    Orden,
    LineaOrden,
    Pago,
    Envio,
)


class VendedorSerializer(serializers.ModelSerializer):
    class Meta:
        model = Vendedor
        fields = ["id", "nombre", "contacto"]


class CategoriaSerializer(serializers.ModelSerializer):
    class Meta:
        model = Categoria
        fields = ["id", "nombre"]


class InstrumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrumento
        fields = ["id", "vendedor", "categoria", "marca", "modelo", "precio_base", "estado_condicion", "estado_venta"]
        read_only_fields = ["estado_venta"]


class ItemCarritoSerializer(serializers.ModelSerializer):
    instrumento = serializers.StringRelatedField(read_only=True)
    instrumento_id = serializers.PrimaryKeyRelatedField(
        source="instrumento", queryset=Instrumento.objects.all(), write_only=True
    )

    class Meta:
        model = ItemCarrito
        fields = ["id", "instrumento", "instrumento_id", "cantidad"]


class CarritoSerializer(serializers.ModelSerializer):
    items = ItemCarritoSerializer(many=True, read_only=True)

    class Meta:
        model = Carrito
        fields = ["id", "comprador", "items"]


class LineaOrdenOutputSerializer(serializers.ModelSerializer):
    instrumento = serializers.StringRelatedField()

    class Meta:
        model = LineaOrden
        fields = ["instrumento", "precio_final"]


class EnvioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Envio
        fields = ["id", "direccion", "estado", "asegurado"]


class PagoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Pago
        fields = ["id", "monto", "metodo"]


class OrdenInputSerializer(serializers.Serializer):
    direccion_envio = serializers.CharField(max_length=255)


class OrdenOutputSerializer(serializers.ModelSerializer):
    lineas = LineaOrdenOutputSerializer(many=True, read_only=True)
    pago = PagoSerializer(read_only=True)
    envio = EnvioSerializer(read_only=True)

    class Meta:
        model = Orden
        fields = ["id", "fecha", "estado", "total", "direccion_envio", "lineas", "pago", "envio"]
