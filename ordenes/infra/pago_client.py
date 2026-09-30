"""
Cliente HTTP hacia el microservicio de Pagos (Flask).

Este cliente es la "costura" (seam) del Strangler Pattern: el monolito ya no
procesa el pago internamente, sino que delega en el microservicio a través de
la red. La URL se configura por variable de entorno para que Docker/Nginx
puedan apuntar al servicio correcto.
"""
import os

import requests


class PagoServiceError(Exception):
    """Error al comunicarse con el microservicio de pagos o pago rechazado."""


class PagoClient:
    def __init__(self, base_url=None, timeout=10):
        # En Docker apunta al gateway Nginx o directamente al servicio Flask.
        self.base_url = base_url or os.environ.get(
            "PAGO_SERVICE_URL", "http://flask_pago_service:5000"
        )
        self.timeout = timeout

    def procesar_pago(self, orden_id, monto, metodo="tarjeta"):
        url = f"{self.base_url}/api/v2/pagos/"
        payload = {"orden_id": orden_id, "monto": float(monto), "metodo": metodo}

        try:
            resp = requests.post(url, json=payload, timeout=self.timeout)
        except requests.RequestException as exc:
            raise PagoServiceError(f"No se pudo contactar al servicio de pagos: {exc}")

        if resp.status_code >= 400:
            try:
                detalle = resp.json().get("detalle", resp.text)
            except ValueError:
                detalle = resp.text
            raise PagoServiceError(f"El servicio de pagos rechazó el pago: {detalle}")

        return resp.json()
