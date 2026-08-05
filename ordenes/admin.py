from django.contrib import admin
from .models import Instrumento, Carrito, ItemCarrito, Orden

admin.site.register(Instrumento)
admin.site.register(Carrito)
admin.site.register(ItemCarrito)
admin.site.register(Orden)
