"""
Integraciones externas desacopladas con el patrón Adapter.

Las vistas dependen de las interfaces (puertos) ConversorDivisas y
ServicioAliado, no de las APIs concretas. Cambiar de proveedor solo
requiere un adaptador nuevo y cambiar la configuración (inversión de
dependencias).
"""
from .aliado import AliadoNoConfigurado, ErrorAliado, ServicioAliado, obtener_servicio_aliado
from .divisas import ConversorDivisas, ErrorDivisas, PrecioService, obtener_conversor

__all__ = [
    "AliadoNoConfigurado",
    "ConversorDivisas",
    "ErrorAliado",
    "ErrorDivisas",
    "PrecioService",
    "ServicioAliado",
    "obtener_conversor",
    "obtener_servicio_aliado",
]
