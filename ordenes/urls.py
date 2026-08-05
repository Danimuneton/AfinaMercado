from django.urls import path
from .views import CrearOrdenView

urlpatterns = [
    path("crear-orden/", CrearOrdenView.as_view(), name="crear_orden"),
]