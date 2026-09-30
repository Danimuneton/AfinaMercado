from django.urls import path
from .views import (
    VendedorListCreateView,
    VendedorDetailView,
    CategoriaListCreateView,
    CategoriaDetailView,
    InstrumentoListCreateView,
    InstrumentoDetailView,
    CarritoDetailView,
    AgregarItemCarritoView,
    OrdenListView,
    OrdenDetailView,
    CrearOrdenView,
)

urlpatterns = [
    # Vendedores
    path("vendedores/", VendedorListCreateView.as_view(), name="vendedores"),
    path("vendedores/<int:pk>/", VendedorDetailView.as_view(), name="vendedor_detail"),
    # Categorías
    path("categorias/", CategoriaListCreateView.as_view(), name="categorias"),
    path("categorias/<int:pk>/", CategoriaDetailView.as_view(), name="categoria_detail"),
    # Instrumentos
    path("instrumentos/", InstrumentoListCreateView.as_view(), name="instrumentos"),
    path("instrumentos/<int:pk>/", InstrumentoDetailView.as_view(), name="instrumento_detail"),
    # Carrito
    path("carrito/", CarritoDetailView.as_view(), name="carrito"),
    path("carrito/items/", AgregarItemCarritoView.as_view(), name="carrito_agregar_item"),
    # Órdenes
    path("ordenes/", OrdenListView.as_view(), name="ordenes"),
    path("ordenes/<int:pk>/", OrdenDetailView.as_view(), name="orden_detail"),
    path("crear-orden/", CrearOrdenView.as_view(), name="crear_orden"),
]
