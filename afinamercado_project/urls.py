from django.contrib import admin
from django.urls import include, path

urlpatterns = [
    path("admin/", admin.site.urls),
    # Cambio de idioma (es / en) mediante el formulario del menú.
    path("i18n/", include("django.conf.urls.i18n")),
    # Monolito legacy (versionado v1). Nginx enruta /api/v1/ hacia Django.
    path("api/v1/", include("ordenes.urls")),
    path("api-auth/", include("rest_framework.urls")),
    # Interfaz web: consume los microservicios v2 a través de la red interna.
    path("", include("web.urls")),
]
