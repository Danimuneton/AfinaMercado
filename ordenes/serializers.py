from rest_framework import serializers
from .models import Instrumento, Orden, LineaOrden


class InstrumentoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Instrumento
        fields = ["id", "vendedor", "categoria", "marca", "modelo", "precio_base", "estado_condicion", "estado_venta"]
        read_only_fields = ["estado_venta"]


class LineaOrdenOutputSerializer(serializers.ModelSerializer):
    instrumento = serializers.StringRelatedField()

    class Meta:
        model = LineaOrden
        fields = ["instrumento", "precio_final"]


class OrdenInputSerializer(serializers.Serializer):
    direccion_envio = serializers.CharField(max_length=255)


class OrdenOutputSerializer(serializers.ModelSerializer):
    lineas = LineaOrdenOutputSerializer(many=True, read_only=True)

    class Meta:
        model = Orden
        fields = ["id", "fecha", "estado", "total", "direccion_envio", "lineas"]