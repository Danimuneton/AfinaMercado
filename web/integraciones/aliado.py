"""
Consumo del servicio del equipo aliado (patrón Adapter).

No sabemos de antemano el formato exacto del JSON del aliado. El adaptador
lo normaliza a una lista de filas simples (columna -> valor) que la vista
puede mostrar en una tabla. Si el formato del aliado cambia, solo se ajusta
este adaptador.
"""
import logging
from abc import ABC, abstractmethod
from dataclasses import dataclass, field

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

MAX_FILAS = 20
MAX_COLUMNAS = 6
CLAVES_LISTA = ("results", "data", "items", "productos", "instrumentos", "elementos", "resultados")


class ErrorAliado(Exception):
    """El servicio del aliado no respondió o respondió algo inválido."""


class AliadoNoConfigurado(ErrorAliado):
    """Aún no se ha configurado ALIADO_API_URL."""


@dataclass
class ResultadoAliado:
    nombre: str
    url: str
    columnas: list = field(default_factory=list)
    filas: list = field(default_factory=list)
    total: int = 0


class ServicioAliado(ABC):
    @abstractmethod
    def obtener(self) -> ResultadoAliado:
        """Trae y normaliza los datos del aliado."""


class AliadoHttpAdapter(ServicioAliado):
    def __init__(self, nombre, url, timeout=6, http=None):
        self.nombre = nombre
        self.url = url
        self.timeout = timeout
        self.http = http or requests

    @staticmethod
    def _extraer_lista(datos):
        if isinstance(datos, list):
            return datos
        if isinstance(datos, dict):
            for clave in CLAVES_LISTA:
                if isinstance(datos.get(clave), list):
                    return datos[clave]
            for valor in datos.values():
                if isinstance(valor, list):
                    return valor
            return [datos]
        raise ErrorAliado("Formato no reconocido")

    @staticmethod
    def _aplanar(elemento):
        if not isinstance(elemento, dict):
            return {"valor": str(elemento)}
        fila = {}
        for clave, valor in elemento.items():
            if isinstance(valor, (str, int, float, bool)) or valor is None:
                fila[str(clave)] = "" if valor is None else str(valor)
            elif isinstance(valor, dict):
                nombre = valor.get("nombre") or valor.get("name")
                if nombre is not None:
                    fila[str(clave)] = str(nombre)
        return fila

    def obtener(self):
        try:
            resp = self.http.get(self.url, timeout=self.timeout, headers={"Accept": "application/json"})
            resp.raise_for_status()
            datos = resp.json()
        except (requests.RequestException, ValueError) as exc:
            logger.warning("Servicio aliado no disponible (%s): %s", self.url, exc)
            raise ErrorAliado(str(exc)) from exc

        elementos = self._extraer_lista(datos)
        filas = [self._aplanar(e) for e in elementos[:MAX_FILAS]]
        columnas = []
        for fila in filas:
            for clave in fila:
                if clave not in columnas and len(columnas) < MAX_COLUMNAS:
                    columnas.append(clave)
        return ResultadoAliado(
            nombre=self.nombre,
            url=self.url,
            columnas=columnas,
            filas=[[fila.get(c, "") for c in columnas] for fila in filas],
            total=len(elementos),
        )


class AliadoSinConfigurar(ServicioAliado):
    def obtener(self):
        raise AliadoNoConfigurado()


def obtener_servicio_aliado() -> ServicioAliado:
    if not settings.ALIADO_API_URL:
        return AliadoSinConfigurar()
    return AliadoHttpAdapter(
        settings.ALIADO_NOMBRE or settings.ALIADO_API_URL,
        settings.ALIADO_API_URL,
        timeout=settings.ALIADO_TIMEOUT,
    )
