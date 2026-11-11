"""
Microservicio de Órdenes y Envíos (Flask) - AfinaMercado.

Extraído del monolito con el Strangler Pattern. Coordina la compra:
  1. Lee el carrito (microservicio Carrito).
  2. Reserva los instrumentos (microservicio Catálogo).
  3. Arma la orden con el patrón Builder y la guarda en su propia BD.
  4. Cobra (microservicio Pagos). Si el pago falla, compensa liberando
     los instrumentos y cancela la orden.
  5. Vacía el carrito y publica un evento asíncrono (Redis/Celery) para
     que el worker envíe la notificación.

Rutas (detrás de Nginx): /api/v2/ordenes/...
"""
import logging
import os
from decimal import Decimal

from flask import Blueprint, Flask, current_app, jsonify, request
from flask_babel import Babel
from flask_babel import gettext as _

from clientes import CarritoClient, CatalogoClient, PagoClient, PublicadorEventos
from comun import (
    ErrorServicio,
    leer_json,
    no_encontrado,
    registrar_manejadores_error,
    requiere_token,
    seleccionar_idioma,
    solicitud_invalida,
)
from models import ESTADOS_ENVIO, METODOS_PAGO, Envio, LineaOrden, Orden, db
from orden_builder import OrdenBuilder

logger = logging.getLogger(__name__)
bp = Blueprint("ordenes", __name__, url_prefix="/api/v2/ordenes")


def _usuario_id():
    try:
        return int(request.headers.get("X-Usuario-Id", ""))
    except ValueError:
        raise solicitud_invalida(_("Falta la cabecera X-Usuario-Id."))


def _validar_entrada(data):
    errores = {}
    direccion = data.get("direccion_envio")
    if not isinstance(direccion, str) or len(direccion.strip()) < 5:
        errores["direccion_envio"] = _("Escribe una dirección de al menos 5 caracteres.")
    elif len(direccion) > 255:
        errores["direccion_envio"] = _("Máximo %(n)s caracteres.", n=255)
    if data.get("metodo_pago") not in METODOS_PAGO:
        errores["metodo_pago"] = _("Método de pago no válido.")
    email = data.get("email") or ""
    if not isinstance(email, str) or len(email) > 254:
        errores["email"] = _("Correo no válido.")
    if errores:
        raise solicitud_invalida(_("Datos de la orden inválidos."), errores)
    return direccion.strip(), data["metodo_pago"], email


@bp.post("/")
@requiere_token
def crear_orden():
    usuario_id = _usuario_id()
    direccion, metodo_pago, email = _validar_entrada(leer_json())

    carrito = CarritoClient().ver(usuario_id)
    ids = [item["instrumento_id"] for item in carrito.get("items", [])]
    if not ids:
        raise solicitud_invalida(_("Tu carrito está vacío."))

    catalogo = CatalogoClient()
    instrumentos = catalogo.reservar(ids)

    try:
        datos = (
            OrdenBuilder(umbral_seguro=current_app.config["UMBRAL_SEGURO"])
            .para_usuario(usuario_id, email)
            .con_lineas(instrumentos)
            .con_envio(direccion)
            .con_metodo_pago(metodo_pago)
            .build()
        )
        orden = Orden(
            usuario_id=usuario_id,
            email=email,
            total=datos["total"],
            direccion_envio=datos["direccion_envio"],
            metodo_pago=metodo_pago,
            lineas=[LineaOrden(**linea) for linea in datos["lineas"]],
            envio=Envio(direccion=datos["direccion_envio"], asegurado=datos["envio_asegurado"]),
        )
        db.session.add(orden)
        db.session.commit()
    except Exception:
        db.session.rollback()
        catalogo.liberar(ids)
        raise

    try:
        pago = PagoClient().procesar(orden.id, orden.total, metodo_pago)
    except ErrorServicio as error:
        # Compensación: la compra no se completó, los instrumentos vuelven a estar disponibles.
        catalogo.liberar(ids)
        orden.estado = "cancelada"
        orden.motivo_cancelacion = error.detalle[:255]
        db.session.commit()
        status = 402 if error.status < 500 else 503
        raise ErrorServicio(
            status,
            "pago_fallido",
            _("No se pudo procesar el pago: %(detalle)s", detalle=error.detalle),
        )

    orden.estado = "pagada"
    orden.transaccion_id = pago.get("transaccion_id")
    db.session.commit()

    try:
        CarritoClient().vaciar(usuario_id)
    except ErrorServicio:
        logger.warning("No se pudo vaciar el carrito del usuario %s", usuario_id)

    respuesta = orden.a_dict()
    respuesta["notificacion_encolada"] = PublicadorEventos.orden_confirmada(
        respuesta, email, seleccionar_idioma()
    )
    return jsonify(respuesta), 201


@bp.get("/")
@requiere_token
def listar_ordenes():
    ordenes = (
        Orden.query.filter_by(usuario_id=_usuario_id())
        .order_by(Orden.fecha.desc(), Orden.id.desc())
        .all()
    )
    return jsonify([o.a_dict() for o in ordenes])


@bp.get("/<int:orden_id>")
@requiere_token
def detalle_orden(orden_id):
    orden = Orden.query.filter_by(id=orden_id, usuario_id=_usuario_id()).first()
    if orden is None:
        raise no_encontrado(_("La orden %(id)s no existe.", id=orden_id))
    return jsonify(orden.a_dict())


@bp.patch("/<int:orden_id>/envio")
@requiere_token
def actualizar_envio(orden_id):
    """Actualiza el estado del envío (uso interno / logística)."""
    estado = leer_json().get("estado")
    if estado not in ESTADOS_ENVIO:
        raise solicitud_invalida(_("Estado de envío no válido."))
    orden = db.session.get(Orden, orden_id)
    if orden is None or orden.envio is None:
        raise no_encontrado(_("La orden %(id)s no existe.", id=orden_id))
    if orden.estado != "pagada":
        raise solicitud_invalida(_("Solo se pueden enviar órdenes pagadas."))
    orden.envio.estado = estado
    db.session.commit()
    return jsonify(orden.a_dict())


@bp.get("/internos/ventas")
@requiere_token
def datos_ventas():
    """Datos crudos de ventas pagadas para el reporte asíncrono del worker."""
    ordenes = Orden.query.filter_by(estado="pagada").all()
    return jsonify(
        [
            {
                "id": o.id,
                "fecha": o.fecha.isoformat(),
                "total": float(o.total),
                "metodo_pago": o.metodo_pago,
                "lineas": [l.a_dict() for l in o.lineas],
            }
            for o in ordenes
        ]
    )


def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///ordenes.db"),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SERVICE_TOKEN=os.environ.get("SERVICE_TOKEN", ""),
        CATALOGO_URL=os.environ.get("CATALOGO_URL", "http://flask_catalogo_service:5000").rstrip("/"),
        CARRITO_URL=os.environ.get("CARRITO_URL", "http://flask_carrito_service:5000").rstrip("/"),
        PAGO_URL=os.environ.get("PAGO_URL", "http://flask_pago_service:5000").rstrip("/"),
        CELERY_BROKER_URL=os.environ.get("CELERY_BROKER_URL", ""),
        UMBRAL_SEGURO=Decimal(os.environ.get("UMBRAL_ENVIO_ASEGURADO", "5000000")),
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
        return jsonify({"status": "ok", "servicio": "ordenes_service"})

    return app


app = create_app()
