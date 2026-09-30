from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, generics
from django.shortcuts import get_object_or_404

from .models import Vendedor, Categoria, Instrumento, Carrito, ItemCarrito, Orden
from .serializers import (
    VendedorSerializer,
    CategoriaSerializer,
    InstrumentoSerializer,
    CarritoSerializer,
    ItemCarritoSerializer,
    OrdenInputSerializer,
    OrdenOutputSerializer,
)
from .services import OrdenService
from .domain.orden_builder import OrdenInvalidaError, InstrumentoNoDisponibleError


# --- Catálogo: Vendedores ---
class VendedorListCreateView(generics.ListCreateAPIView):
    queryset = Vendedor.objects.all()
    serializer_class = VendedorSerializer


class VendedorDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Vendedor.objects.all()
    serializer_class = VendedorSerializer


# --- Catálogo: Categorías ---
class CategoriaListCreateView(generics.ListCreateAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer


class CategoriaDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Categoria.objects.all()
    serializer_class = CategoriaSerializer


# --- Catálogo: Instrumentos ---
class InstrumentoListCreateView(generics.ListCreateAPIView):
    queryset = Instrumento.objects.all()
    serializer_class = InstrumentoSerializer


class InstrumentoDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Instrumento.objects.all()
    serializer_class = InstrumentoSerializer


# --- Carrito de compras ---
class CarritoDetailView(APIView):
    """Devuelve (o crea) el carrito del comprador autenticado."""

    def get(self, request):
        carrito, _ = Carrito.objects.get_or_create(comprador=request.user)
        return Response(CarritoSerializer(carrito).data)


class AgregarItemCarritoView(APIView):
    """Agrega un instrumento al carrito del comprador autenticado."""

    def post(self, request):
        serializer = ItemCarritoSerializer(data=request.data)
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        carrito, _ = Carrito.objects.get_or_create(comprador=request.user)
        ItemCarrito.objects.create(
            carrito=carrito,
            instrumento=serializer.validated_data["instrumento"],
            cantidad=serializer.validated_data.get("cantidad", 1),
        )
        return Response(CarritoSerializer(carrito).data, status=status.HTTP_201_CREATED)


# --- Órdenes ---
class OrdenListView(generics.ListAPIView):
    serializer_class = OrdenOutputSerializer

    def get_queryset(self):
        return Orden.objects.filter(comprador=self.request.user)


class OrdenDetailView(generics.RetrieveAPIView):
    serializer_class = OrdenOutputSerializer

    def get_queryset(self):
        return Orden.objects.filter(comprador=self.request.user)


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
