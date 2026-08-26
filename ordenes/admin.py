from django.contrib import admin
from .models import Vendedor, Categoria, Instrumento, Carrito, ItemCarrito, Orden, LineaOrden, Pago, Envio

admin.site.register(Vendedor)
admin.site.register(Categoria)
admin.site.register(Instrumento)
admin.site.register(Carrito)
admin.site.register(ItemCarrito)
admin.site.register(Orden)
admin.site.register(LineaOrden)
admin.site.register(Pago)
admin.site.register(Envio)