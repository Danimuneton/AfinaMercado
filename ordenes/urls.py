from django.urls import path
from .views import InstrumentoListCreateView, CrearOrdenView

urlpatterns = [
    path("instrumentos/", InstrumentoListCreateView.as_view(), name="instrumentos"),
    path("crear-orden/", CrearOrdenView.as_view(), name="crear_orden"),
]