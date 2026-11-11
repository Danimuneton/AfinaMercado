"""
Microservicio de Carrito de compras (Flask) - AfinaMercado.

Extraído del monolito con el Strangler Pattern. Guarda los instrumentos que
cada usuario quiere comprar, en su propia base de datos. Consulta al
microservicio de Catálogo para validar que el instrumento exista y esté
disponible.

Rutas (detrás de Nginx): /api/v2/carrito/...
"""
import os
from datetime import datetime, timezone
from decimal import Decimal

import requests
from flask import Blueprint, Flask, current_app, jsonify, request
from flask_babel import Babel
from flask_babel import gettext as _
from flask_sqlalchemy import SQLAlchemy

from comun import (
    ErrorServicio,
    conflicto,
    leer_json,
    no_encontrado,
    registrar_manejadores_error,
    requiere_token,
    seleccionar_idioma,
    solicitud_invalida,
)

db = SQLAlchemy()
bp = Blueprint("carrito", __name__, url_prefix="/api/v2/carrito")


class ItemCarrito(db.Model):
    __tablename__ = "items_carrito"
    __table_args__ = (db.UniqueConstraint("usuario_id", "instrumento_id"),)

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False, index=True)
    instrumento_id = db.Column(db.Integer, nullable=False)
    # Copia de los datos al momento de agregar (el precio definitivo lo da Catálogo al comprar).
    marca = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    precio = db.Column(db.Numeric(12, 2), nullable=False)
    agregado_en = db.Column(
        db.DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc)
    )

    def a_dict(self):
        return {
            "instrumento_id": self.instrumento_id,
            "marca": self.marca,
            "modelo": self.modelo,
            "precio": float(self.precio),
            "agregado_en": self.agregado_en.isoformat() if self.agregado_en else None,
        }


def _usuario_id():
    try:
        return int(request.headers.get("X-Usuario-Id", ""))
    except ValueError:
        raise solicitud_invalida(_("Falta la cabecera X-Usuario-Id."))


def _consultar_instrumento(instrumento_id):
    url = f"{current_app.config['CATALOGO_URL']}/api/v2/catalogo/instrumentos/{instrumento_id}"
    try:
        resp = requests.get(url, timeout=5, headers={"Accept-Language": seleccionar_idioma()})
    except requests.RequestException:
        raise ErrorServicio(
            503, "servicio_no_disponible", _("El catálogo no está disponible en este momento.")
        )
    if resp.status_code == 404:
        raise no_encontrado(_("El instrumento %(id)s no existe.", id=instrumento_id))
    if resp.status_code != 200:
        raise ErrorServicio(
            502, "error_dependencia", _("El catálogo respondió con un error.")
        )
    return resp.json()


def _respuesta_carrito(usuario_id):
    items = (
        ItemCarrito.query.filter_by(usuario_id=usuario_id)
        .order_by(ItemCarrito.agregado_en)
        .all()
    )
    total = sum((i.precio for i in items), Decimal("0"))
    return {
        "usuario_id": usuario_id,
        "items": [i.a_dict() for i in items],
        "cantidad": len(items),
        "total": float(total),
        "moneda": "COP",
    }


@bp.get("/")
@requiere_token
def ver_carrito():
    return jsonify(_respuesta_carrito(_usuario_id()))


@bp.post("/items")
@requiere_token
def agregar_item():
    usuario_id = _usuario_id()
    data = leer_json()
    try:
        instrumento_id = int(data.get("instrumento_id"))
    except (TypeError, ValueError):
        raise solicitud_invalida(
            _("Datos inválidos."), {"instrumento_id": _("Debe ser un número entero.")}
        )

    if ItemCarrito.query.filter_by(usuario_id=usuario_id, instrumento_id=instrumento_id).first():
        raise conflicto(_("Este instrumento ya está en tu carrito."))

    instrumento = _consultar_instrumento(instrumento_id)
    if instrumento.get("estado_venta") != "disponible":
        raise conflicto(_("Este instrumento ya fue vendido."))
    vendedor = instrumento.get("vendedor") or {}
    if vendedor.get("usuario_id") == usuario_id:
        raise conflicto(_("No puedes comprar un instrumento que tú publicaste."))

    item = ItemCarrito(
        usuario_id=usuario_id,
        instrumento_id=instrumento_id,
        marca=instrumento["marca"],
        modelo=instrumento["modelo"],
        precio=Decimal(str(instrumento["precio_base"])),
    )
    db.session.add(item)
    db.session.commit()
    return jsonify(_respuesta_carrito(usuario_id)), 201


@bp.delete("/items/<int:instrumento_id>")
@requiere_token
def quitar_item(instrumento_id):
    usuario_id = _usuario_id()
    item = ItemCarrito.query.filter_by(usuario_id=usuario_id, instrumento_id=instrumento_id).first()
    if item is None:
        raise no_encontrado(_("Ese instrumento no está en tu carrito."))
    db.session.delete(item)
    db.session.commit()
    return jsonify(_respuesta_carrito(usuario_id))


@bp.delete("/")
@requiere_token
def vaciar_carrito():
    usuario_id = _usuario_id()
    ItemCarrito.query.filter_by(usuario_id=usuario_id).delete()
    db.session.commit()
    return jsonify(_respuesta_carrito(usuario_id))


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///carrito.db"),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SERVICE_TOKEN=os.environ.get("SERVICE_TOKEN", ""),
        CATALOGO_URL=os.environ.get("CATALOGO_URL", "http://flask_catalogo_service:5000").rstrip("/"),
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
        return jsonify({"status": "ok", "servicio": "carrito_service"})

    return app


app = create_app()
