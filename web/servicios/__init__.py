"""Clientes HTTP hacia los microservicios Flask (Strangler Pattern)."""
from .base import ErrorMicroservicio, MicroservicioNoDisponible
from .carrito import CarritoServicio
from .catalogo import CatalogoServicio
from .ordenes import OrdenesServicio

__all__ = [
    "CarritoServicio",
    "CatalogoServicio",
    "ErrorMicroservicio",
    "MicroservicioNoDisponible",
    "OrdenesServicio",
]
