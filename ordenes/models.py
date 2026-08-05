from django.db import models
from django.contrib.auth.models import User


class Instrumento(models.Model):
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2)
    estado_condicion = models.CharField(max_length=50)
    estado_venta = models.CharField(max_length=20, default="disponible")

    def __str__(self):
        return f"{self.marca} {self.modelo}"


class Carrito(models.Model):
    comprador = models.ForeignKey(User, on_delete=models.CASCADE)


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, related_name="items", on_delete=models.CASCADE)
    instrumento = models.ForeignKey(Instrumento, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)


class Orden(models.Model):
    comprador = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=50, default="creada")
    total = models.DecimalField(max_digits=10, decimal_places=2)
    direccion_envio = models.CharField(max_length=255)