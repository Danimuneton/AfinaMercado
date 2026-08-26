from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.shortcuts import get_object_or_404

from .models import Carrito, Instrumento
from .serializers import InstrumentoSerializer, OrdenInputSerializer, OrdenOutputSerializer
from .services import OrdenService
from .domain.orden_builder import OrdenInvalidaError, InstrumentoNoDisponibleError


class InstrumentoListCreateView(generics.ListCreateAPIView):
    queryset = Instrumento.objects.all()
    serializer_class = InstrumentoSerializer


class CrearOrdenView(APIView):
    def post(self, request):
        input_serializer = OrdenInputSerializer(data=request.data)
        if not input_serializer.is_valid():
            return Response(input_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        carrito = get_object_or_404(Carrito, comprador=request.user)

        try:
            orden = OrdenService().crear_orden_desde_carrito(
                comprador=request.user,
                carrito=carrito,
                direccion_envio=input_serializer.validated_data["direccion_envio"],
            )
        except InstrumentoNoDisponibleError as e:
            return Response({"error": str(e)}, status=status.HTTP_409_CONFLICT)
        except OrdenInvalidaError as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

        return Response(OrdenOutputSerializer(orden).data, status=status.HTTP_201_CREATED)