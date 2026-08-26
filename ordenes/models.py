from django.db import models
from django.contrib.auth.models import User
from django.core.validators import MinValueValidator


class Vendedor(models.Model):
    nombre = models.CharField(max_length=150)
    contacto = models.CharField(max_length=150)

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class Instrumento(models.Model):
    ESTADOS_CONDICION = [
        ("excelente", "Excelente"),
        ("bueno", "Bueno"),
        ("regular", "Regular"),
    ]
    ESTADOS_VENTA = [
        ("disponible", "Disponible"),
        ("vendido", "Vendido"),
    ]

    vendedor = models.ForeignKey(Vendedor, related_name="instrumentos", on_delete=models.CASCADE)
    categoria = models.ForeignKey(Categoria, related_name="instrumentos", on_delete=models.PROTECT)
    marca = models.CharField(max_length=100)
    modelo = models.CharField(max_length=100)
    precio_base = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0.01)])
    estado_condicion = models.CharField(max_length=20, choices=ESTADOS_CONDICION)
    estado_venta = models.CharField(max_length=20, choices=ESTADOS_VENTA, default="disponible")

    def __str__(self):
        return f"{self.marca} {self.modelo}"


class Carrito(models.Model):
    comprador = models.OneToOneField(User, on_delete=models.CASCADE)


class ItemCarrito(models.Model):
    carrito = models.ForeignKey(Carrito, related_name="items", on_delete=models.CASCADE)
    instrumento = models.ForeignKey(Instrumento, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField(default=1)


class Orden(models.Model):
    ESTADOS = [
        ("creada", "Creada"),
        ("pagada", "Pagada"),
        ("cancelada", "Cancelada"),
    ]
    comprador = models.ForeignKey(User, related_name="ordenes", on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="creada")
    total = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    direccion_envio = models.CharField(max_length=255)

    def __str__(self):
        return f"Orden #{self.id} - {self.comprador}"


class LineaOrden(models.Model):
    orden = models.ForeignKey(Orden, related_name="lineas", on_delete=models.CASCADE)
    instrumento = models.ForeignKey(Instrumento, on_delete=models.PROTECT)
    precio_final = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])


class Pago(models.Model):
    METODOS = [("tarjeta", "Tarjeta"), ("transferencia", "Transferencia")]
    orden = models.OneToOneField(Orden, related_name="pago", on_delete=models.CASCADE)
    monto = models.DecimalField(max_digits=10, decimal_places=2, validators=[MinValueValidator(0)])
    metodo = models.CharField(max_length=20, choices=METODOS, default="tarjeta")


class Envio(models.Model):
    ESTADOS = [("pendiente", "Pendiente"), ("en_camino", "En camino"), ("entregado", "Entregado")]
    orden = models.OneToOneField(Orden, related_name="envio", on_delete=models.CASCADE)
    direccion = models.CharField(max_length=255)
    estado = models.CharField(max_length=20, choices=ESTADOS, default="pendiente")
    asegurado = models.BooleanField(default=False)