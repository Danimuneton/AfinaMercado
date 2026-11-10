"""
API de terceros: tasas de cambio (patrón Adapter + inversión de dependencias).

    PrecioService  ──depende de──▶  ConversorDivisas (interfaz / puerto)
                                          ▲                ▲
                         ExchangeRateApiAdapter      TasaFijaAdapter
                         (open.er-api.com)           (sin red, pruebas)

El dominio solo conoce ConversorDivisas.tasa(origen, destino). Cada adaptador
traduce el formato propio del proveedor a esa interfaz.
"""
import logging
from abc import ABC, abstractmethod
from decimal import Decimal, InvalidOperation

import requests
from django.conf import settings
from django.core.cache import cache

logger = logging.getLogger(__name__)


class ErrorDivisas(Exception):
    """No fue posible obtener la tasa de cambio."""


class ConversorDivisas(ABC):
    """Puerto: lo único que el sistema necesita saber de un proveedor de divisas."""

    @abstractmethod
    def tasa(self, origen: str, destino: str) -> Decimal:
        """Cuántas unidades de `destino` equivalen a 1 unidad de `origen`."""

    def convertir(self, monto, origen: str, destino: str) -> Decimal:
        return (Decimal(str(monto)) * self.tasa(origen, destino)).quantize(Decimal("0.01"))


class ExchangeRateApiAdapter(ConversorDivisas):
    """
    Adaptador para la API pública de ExchangeRate-API (https://open.er-api.com).
    Respuesta del proveedor: {"result": "success", "base_code": "COP", "rates": {"USD": 0.00025, ...}}
    """

    def __init__(self, url_base, timeout=5, cache_segundos=3600, http=None):
        self.url_base = url_base.rstrip("/")
        self.timeout = timeout
        self.cache_segundos = cache_segundos
        self.http = http or requests

    def _tasas(self, origen):
        clave = f"divisas:tasas:{origen}"
        tasas = cache.get(clave)
        if tasas is not None:
            return tasas
        try:
            resp = self.http.get(f"{self.url_base}/{origen}", timeout=self.timeout)
            resp.raise_for_status()
            datos = resp.json()
        except (requests.RequestException, ValueError) as exc:
            raise ErrorDivisas(f"Proveedor de divisas sin respuesta: {exc}") from exc
        if datos.get("result") != "success" or not isinstance(datos.get("rates"), dict):
            raise ErrorDivisas(f"Respuesta inesperada del proveedor: {datos.get('error-type', datos)}")
        tasas = datos["rates"]
        cache.set(clave, tasas, self.cache_segundos)
        return tasas

    def tasa(self, origen, destino):
        tasas = self._tasas(origen.upper())
        try:
            return Decimal(str(tasas[destino.upper()]))
        except (KeyError, InvalidOperation) as exc:
            raise ErrorDivisas(f"Moneda no soportada: {destino}") from exc


class TasaFijaAdapter(ConversorDivisas):
    """Adaptador sin red: usa tasas configuradas (útil para pruebas o sin internet)."""

    def __init__(self, tasas):
        self.tasas = {(o.upper(), d.upper()): Decimal(str(t)) for (o, d), t in tasas.items()}

    def tasa(self, origen, destino):
        if origen.upper() == destino.upper():
            return Decimal("1")
        try:
            return self.tasas[(origen.upper(), destino.upper())]
        except KeyError as exc:
            raise ErrorDivisas(f"Tasa no configurada: {origen}->{destino}") from exc


def obtener_conversor() -> ConversorDivisas:
    """Elige el adaptador concreto según la configuración (punto único de cambio)."""
    if settings.DIVISAS_PROVEEDOR == "tasa_fija":
        return TasaFijaAdapter({("COP", "USD"): settings.DIVISAS_TASA_FIJA_USD})
    return ExchangeRateApiAdapter(
        settings.DIVISAS_API_URL, cache_segundos=settings.DIVISAS_CACHE_SEGUNDOS
    )


class PrecioService:
    """Caso de uso: mostrar el precio equivalente en otra moneda."""

    def __init__(self, conversor: ConversorDivisas):
        self.conversor = conversor

    def equivalente(self, monto_cop, moneda="USD"):
        """Devuelve el monto convertido o None si el proveedor falla (la página sigue funcionando)."""
        try:
            return self.conversor.convertir(monto_cop, "COP", moneda)
        except ErrorDivisas as exc:
            logger.warning("Conversión de divisas no disponible: %s", exc)
            return None
