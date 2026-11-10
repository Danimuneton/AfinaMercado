from django.contrib.auth import views as auth_views
from django.urls import path

from . import views
from .forms import LoginForm

app_name = "web"

urlpatterns = [
    path("", views.catalogo, name="catalogo"),
    path("catalogo/<int:instrumento_id>/", views.instrumento_detalle, name="instrumento"),
    path("publicar/", views.publicar, name="publicar"),
    path("mis-publicaciones/", views.mis_publicaciones, name="mis_publicaciones"),
    path("carrito/", views.carrito, name="carrito"),
    path("carrito/agregar/<int:instrumento_id>/", views.carrito_agregar, name="carrito_agregar"),
    path("carrito/quitar/<int:instrumento_id>/", views.carrito_quitar, name="carrito_quitar"),
    path("checkout/", views.checkout, name="checkout"),
    path("mis-ordenes/", views.ordenes, name="ordenes"),
    path("mis-ordenes/<int:orden_id>/", views.orden_detalle, name="orden"),
    path("aliado/", views.aliado, name="aliado"),
    path("reportes/", views.reportes, name="reportes"),
    path("reportes/<str:tarea_id>/", views.reporte_estado, name="reporte_estado"),
    path("cuenta/registro/", views.registro, name="registro"),
    path(
        "cuenta/ingresar/",
        auth_views.LoginView.as_view(
            template_name="web/login.html", authentication_form=LoginForm, redirect_authenticated_user=True
        ),
        name="login",
    ),
    path("cuenta/salir/", auth_views.LogoutView.as_view(), name="logout"),
    path("salud/", views.salud, name="salud"),
]
