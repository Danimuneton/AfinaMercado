"""
Microservicio de Pagos (Strangler Pattern) - AfinaMercado.

Este servicio Flask extrae la lógica de "procesamiento de pagos" que antes
vivía dentro del monolito Django. Expone una API REST que recibe y responde
JSON nativo, y maneja los errores de forma estructurada (400 / 404 / 500)
para garantizar resiliencia.

Ruta principal (detrás de Nginx): POST /api/v2/pagos/
"""
import os
import uuid
from datetime import datetime, timezone

from flask import Flask, jsonify, request

app = Flask(__name__)

# Métodos de pago soportados por el servicio (regla de negocio propia del microservicio).
METODOS_VALIDOS = {"tarjeta", "transferencia", "pse", "nequi"}


class PagoInvalidoError(Exception):
    """Datos de pago incompletos o inválidos -> HTTP 400."""


class PasarelaRechazadaError(Exception):
    """La pasarela de pagos rechazó la transacción -> HTTP 402."""


def _validar_payload(data):
    """Valida el JSON de entrada. Lanza PagoInvalidoError con mensaje claro."""
    if not isinstance(data, dict):
        raise PagoInvalidoError("El cuerpo de la petición debe ser un objeto JSON.")

    orden_id = data.get("orden_id")
    monto = data.get("monto")
    metodo = data.get("metodo")

    if orden_id is None:
        raise PagoInvalidoError("El campo 'orden_id' es obligatorio.")

    if monto is None:
        raise PagoInvalidoError("El campo 'monto' es obligatorio.")
    try:
        monto = float(monto)
    except (TypeError, ValueError):
        raise PagoInvalidoError("El campo 'monto' debe ser numérico.")
    if monto <= 0:
        raise PagoInvalidoError("El campo 'monto' debe ser mayor que 0.")

    if metodo is None:
        raise PagoInvalidoError("El campo 'metodo' es obligatorio.")
    if metodo not in METODOS_VALIDOS:
        raise PagoInvalidoError(
            f"Método '{metodo}' no soportado. Válidos: {sorted(METODOS_VALIDOS)}."
        )

    return {"orden_id": orden_id, "monto": monto, "metodo": metodo}


def _procesar_con_pasarela(pago):
    """
    Simula la comunicación con una pasarela de pagos externa.
    Aquí es donde vive el trabajo 'pesado' que bloqueaba a Django.
    Regla simulada: montos absurdamente altos se rechazan (fraude).
    """
    if pago["monto"] > 1_000_000_000:
        raise PasarelaRechazadaError("Transacción rechazada por la pasarela (monto sospechoso).")

    return {
        "transaccion_id": str(uuid.uuid4()),
        "autorizado": True,
    }


@app.route("/health", methods=["GET"])
def health():
    """Healthcheck del microservicio."""
    return jsonify({"status": "ok", "servicio": "pago_service"}), 200


@app.route("/api/v2/pagos/", methods=["POST"])
def procesar_pago():
    """
    Procesa un pago. Recibe y responde JSON nativo.
    Body esperado: {"orden_id": 1, "monto": 150.0, "metodo": "tarjeta"}
    """
    data = request.get_json(silent=True)
    pago = _validar_payload(data)
    resultado = _procesar_con_pasarela(pago)

    return (
        jsonify(
            {
                "estado": "aprobado",
                "orden_id": pago["orden_id"],
                "monto": pago["monto"],
                "metodo": pago["metodo"],
                "transaccion_id": resultado["transaccion_id"],
                "procesado_en": datetime.now(timezone.utc).isoformat(),
            }
        ),
        201,
    )


# ---------------------------------------------------------------------------
# Manejo de errores estructurado (resiliencia)
# ---------------------------------------------------------------------------
@app.errorhandler(PagoInvalidoError)
def handle_pago_invalido(error):
    return jsonify({"error": "solicitud_invalida", "detalle": str(error)}), 400


@app.errorhandler(PasarelaRechazadaError)
def handle_pasarela_rechazada(error):
    return jsonify({"error": "pago_rechazado", "detalle": str(error)}), 402


@app.errorhandler(404)
def handle_not_found(error):
    return jsonify({"error": "no_encontrado", "detalle": "Recurso no encontrado."}), 404


@app.errorhandler(405)
def handle_method_not_allowed(error):
    return jsonify({"error": "metodo_no_permitido", "detalle": "Método HTTP no permitido en esta ruta."}), 405


@app.errorhandler(Exception)
def handle_error_interno(error):
    # Cualquier excepción no controlada -> 500 estructurado.
    return jsonify({"error": "error_interno", "detalle": "Ocurrió un error inesperado en el servicio de pagos."}), 500


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)
