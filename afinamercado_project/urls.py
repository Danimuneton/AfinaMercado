from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),
    # Monolito legacy (versionado v1). Nginx enruta /api/v1/ hacia Django.
    path('api/v1/', include('ordenes.urls')),
    path('api-auth/', include('rest_framework.urls')),
]
