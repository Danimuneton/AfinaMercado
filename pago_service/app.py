"""
Microservicio de Pagos (Strangler Pattern) - AfinaMercado.

Primer módulo extraído del monolito (Taller 02). Procesa pagos contra una
pasarela simulada, guarda cada transacción en su propia base de datos y
responde JSON con errores estructurados (400 / 402 / 404 / 405 / 500).

Rutas (detrás de Nginx): /api/v2/pagos/...
"""
import os
import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, Flask, jsonify, request
from flask_babel import Babel
from flask_babel import gettext as _
from flask_sqlalchemy import SQLAlchemy

from comun import (
    ErrorServicio,
    leer_json,
    no_encontrado,
    registrar_manejadores_error,
    seleccionar_idioma,
    solicitud_invalida,
)

db = SQLAlchemy()
bp = Blueprint("pagos", __name__, url_prefix="/api/v2/pagos")

METODOS_VALIDOS = ("tarjeta", "transferencia", "pse", "nequi")
LIMITE_FRAUDE = Decimal("1000000000")


class Pago(db.Model):
    __tablename__ = "pagos"

    id = db.Column(db.Integer, primary_key=True)
    transaccion_id = db.Column(db.String(64), unique=True, nullable=False)
    orden_id = db.Column(db.Integer, nullable=False, index=True)
    monto = db.Column(db.Numeric(14, 2), nullable=False)
    metodo = db.Column(db.String(20), nullable=False)
    estado = db.Column(db.String(20), nullable=False)
    procesado_en = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def a_dict(self):
        return {
            "estado": self.estado,
            "orden_id": self.orden_id,
            "monto": float(self.monto),
            "metodo": self.metodo,
            "transaccion_id": self.transaccion_id,
            "procesado_en": self.procesado_en.isoformat() if self.procesado_en else None,
        }


def _validar_payload(data):
    """Valida el JSON de entrada. Lanza un error 400 con un mensaje claro."""
    orden_id = data.get("orden_id")
    monto = data.get("monto")
    metodo = data.get("metodo")

    if orden_id is None:
        raise solicitud_invalida(_("El campo 'orden_id' es obligatorio."))
    try:
        orden_id = int(orden_id)
    except (TypeError, ValueError):
        raise solicitud_invalida(_("El campo 'orden_id' debe ser un número entero."))

    if monto is None:
        raise solicitud_invalida(_("El campo 'monto' es obligatorio."))
    try:
        monto = Decimal(str(monto))
    except (InvalidOperation, ValueError):
        raise solicitud_invalida(_("El campo 'monto' debe ser numérico."))
    if not monto.is_finite() or monto <= 0:
        raise solicitud_invalida(_("El campo 'monto' debe ser mayor que 0."))

    if metodo is None:
        raise solicitud_invalida(_("El campo 'metodo' es obligatorio."))
    if metodo not in METODOS_VALIDOS:
        raise solicitud_invalida(
            _("Método '%(metodo)s' no soportado. Válidos: %(validos)s.",
              metodo=metodo, validos=", ".join(METODOS_VALIDOS))
        )
    return {"orden_id": orden_id, "monto": monto.quantize(Decimal("0.01")), "metodo": metodo}


def _procesar_con_pasarela(pago):
    """
    Simula la pasarela de pagos externa (el trabajo "pesado" que bloqueaba
    a Django). Regla simulada: montos absurdamente altos se rechazan (fraude).
    """
    return pago["monto"] <= LIMITE_FRAUDE


@bp.post("/")
def procesar_pago():
    """Body: {"orden_id": 1, "monto": 150.0, "metodo": "tarjeta"}"""
    datos = _validar_payload(leer_json())
    aprobado = _procesar_con_pasarela(datos)

    pago = Pago(
        transaccion_id=str(uuid.uuid4()),
        orden_id=datos["orden_id"],
        monto=datos["monto"],
        metodo=datos["metodo"],
        estado="aprobado" if aprobado else "rechazado",
    )
    db.session.add(pago)
    db.session.commit()

    if not aprobado:
        raise ErrorServicio(
            402, "pago_rechazado", _("Transacción rechazada por la pasarela (monto sospechoso).")
        )
    return jsonify(pago.a_dict()), 201


@bp.get("/")
def listar_pagos():
    """Consulta de pagos, opcionalmente filtrados por ?orden_id=."""
    consulta = Pago.query
    orden_id = request.args.get("orden_id", type=int)
    if orden_id:
        consulta = consulta.filter_by(orden_id=orden_id)
    pagos = consulta.order_by(Pago.procesado_en.desc()).limit(100).all()
    return jsonify([p.a_dict() for p in pagos])


@bp.get("/<transaccion_id>")
def detalle_pago(transaccion_id):
    pago = Pago.query.filter_by(transaccion_id=transaccion_id).first()
    if pago is None:
        raise no_encontrado(_("La transacción no existe."))
    return jsonify(pago.a_dict())


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///pagos.db"),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SERVICE_TOKEN=os.environ.get("SERVICE_TOKEN", ""),
        BABEL_DEFAULT_LOCALE="es",
        BABEL_TRANSLATION_DIRECTORIES=os.path.join(os.path.dirname(__file__), "translations"),
    )
    app.json.ensure_ascii = False
    app.json.sort_keys = False
    if config:
        app.config.update(config)

    db.init_app(app)
    Babel(app, locale_selector=seleccionar_idioma)
    registrar_manejadores_error(app, db)
    app.register_blueprint(bp)

    @app.get("/health")
    def health():
        return jsonify({"status": "ok", "servicio": "pago_service"})

    return app


app = create_app()
