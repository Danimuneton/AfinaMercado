"""
Microservicio de Catálogo (Flask) - AfinaMercado.

Extraído del monolito Django con el Strangler Pattern. Es dueño de los datos
de vendedores, categorías e instrumentos (base de datos propia).

Rutas (detrás de Nginx): /api/v2/catalogo/...
"""
import os
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from flask import Blueprint, Flask, jsonify, request
from flask_babel import Babel
from flask_babel import gettext as _
from sqlalchemy import or_

from comun import (
    conflicto,
    leer_json,
    no_encontrado,
    registrar_manejadores_error,
    requiere_token,
    seleccionar_idioma,
    solicitud_invalida,
)
from models import CONDICIONES, Categoria, Instrumento, Vendedor, db

PRECIO_MAXIMO = Decimal("10000000000")

bp = Blueprint("catalogo", __name__, url_prefix="/api/v2/catalogo")


# ---------------------------------------------------------------------------
# Validaciones
# ---------------------------------------------------------------------------
def _texto(data, campo, errores, maximo, obligatorio=True):
    valor = data.get(campo)
    if valor is None or (isinstance(valor, str) and not valor.strip()):
        if obligatorio:
            errores[campo] = _("Este campo es obligatorio.")
        return ""
    if not isinstance(valor, str):
        errores[campo] = _("Debe ser un texto.")
        return ""
    valor = valor.strip()
    if len(valor) > maximo:
        errores[campo] = _("Máximo %(n)s caracteres.", n=maximo)
    return valor


def _entero(data, campo, errores):
    valor = data.get(campo)
    if isinstance(valor, bool):
        valor = None
    try:
        return int(valor)
    except (TypeError, ValueError):
        errores[campo] = _("Debe ser un número entero.")
        return None


def _lista_ids(data):
    ids = data.get("ids")
    if not isinstance(ids, list) or not ids:
        raise solicitud_invalida(_("El campo 'ids' debe ser una lista no vacía."))
    try:
        return sorted({int(i) for i in ids})
    except (TypeError, ValueError):
        raise solicitud_invalida(_("Todos los ids deben ser números enteros."))


def _obtener_instrumento(instrumento_id):
    instrumento = db.session.get(Instrumento, instrumento_id)
    if instrumento is None:
        raise no_encontrado(_("El instrumento %(id)s no existe.", id=instrumento_id))
    return instrumento


# ---------------------------------------------------------------------------
# Vendedores
# ---------------------------------------------------------------------------
@bp.get("/vendedores")
def listar_vendedores():
    return jsonify([v.a_dict() for v in Vendedor.query.order_by(Vendedor.nombre).all()])


@bp.post("/vendedores/sincronizar")
@requiere_token
def sincronizar_vendedor():
    """Obtiene o crea el perfil de vendedor asociado a un usuario de Django."""
    data = leer_json()
    errores = {}
    usuario_id = _entero(data, "usuario_id", errores)
    nombre = _texto(data, "nombre", errores, 150)
    contacto = _texto(data, "contacto", errores, 150, obligatorio=False)
    if errores:
        raise solicitud_invalida(_("Datos de vendedor inválidos."), errores)

    vendedor = Vendedor.query.filter_by(usuario_id=usuario_id).first()
    creado = vendedor is None
    if creado:
        vendedor = Vendedor(usuario_id=usuario_id, nombre=nombre, contacto=contacto)
        db.session.add(vendedor)
    else:
        vendedor.nombre = nombre
        vendedor.contacto = contacto or vendedor.contacto
    db.session.commit()
    return jsonify(vendedor.a_dict()), 201 if creado else 200


# ---------------------------------------------------------------------------
# Categorías
# ---------------------------------------------------------------------------
@bp.get("/categorias")
def listar_categorias():
    return jsonify([c.a_dict() for c in Categoria.query.order_by(Categoria.nombre).all()])


@bp.post("/categorias")
@requiere_token
def crear_categoria():
    data = leer_json()
    errores = {}
    nombre = _texto(data, "nombre", errores, 100)
    if errores:
        raise solicitud_invalida(_("Datos de categoría inválidos."), errores)
    if Categoria.query.filter(Categoria.nombre.ilike(nombre)).first():
        raise conflicto(_("Ya existe una categoría con ese nombre."))
    categoria = Categoria(nombre=nombre)
    db.session.add(categoria)
    db.session.commit()
    return jsonify(categoria.a_dict()), 201


# ---------------------------------------------------------------------------
# Instrumentos
# ---------------------------------------------------------------------------
@bp.get("/instrumentos")
def listar_instrumentos():
    consulta = Instrumento.query

    estado = request.args.get("estado", "disponible")
    if estado != "todos":
        consulta = consulta.filter(Instrumento.estado_venta == estado)

    categoria_id = request.args.get("categoria_id", type=int)
    if categoria_id:
        consulta = consulta.filter(Instrumento.categoria_id == categoria_id)

    usuario_id = request.args.get("vendedor_usuario_id", type=int)
    if usuario_id:
        consulta = consulta.join(Vendedor).filter(Vendedor.usuario_id == usuario_id)

    texto = (request.args.get("q") or "").strip()
    if texto:
        patron = f"%{texto}%"
        consulta = consulta.filter(
            or_(Instrumento.marca.ilike(patron), Instrumento.modelo.ilike(patron))
        )

    instrumentos = consulta.order_by(Instrumento.creado_en.desc(), Instrumento.id.desc()).all()
    return jsonify([i.a_dict() for i in instrumentos])


@bp.get("/instrumentos/<int:instrumento_id>")
def detalle_instrumento(instrumento_id):
    return jsonify(_obtener_instrumento(instrumento_id).a_dict())


@bp.post("/instrumentos")
@requiere_token
def crear_instrumento():
    data = leer_json()
    errores = {}
    marca = _texto(data, "marca", errores, 100)
    modelo = _texto(data, "modelo", errores, 100)
    descripcion = _texto(data, "descripcion", errores, 2000, obligatorio=False)
    vendedor_id = _entero(data, "vendedor_id", errores)
    categoria_id = _entero(data, "categoria_id", errores)

    condicion = data.get("estado_condicion")
    if condicion not in CONDICIONES:
        errores["estado_condicion"] = _("Condición no válida.")

    precio = None
    try:
        precio = Decimal(str(data.get("precio_base")))
        if not precio.is_finite() or precio <= 0:
            errores["precio_base"] = _("El precio debe ser mayor que 0.")
        elif precio > PRECIO_MAXIMO:
            errores["precio_base"] = _("El precio es demasiado alto.")
    except (InvalidOperation, ValueError):
        errores["precio_base"] = _("El precio debe ser numérico.")

    if vendedor_id is not None and db.session.get(Vendedor, vendedor_id) is None:
        errores["vendedor_id"] = _("El vendedor no existe.")
    if categoria_id is not None and db.session.get(Categoria, categoria_id) is None:
        errores["categoria_id"] = _("La categoría no existe.")

    if errores:
        raise solicitud_invalida(_("Datos de instrumento inválidos."), errores)

    instrumento = Instrumento(
        vendedor_id=vendedor_id,
        categoria_id=categoria_id,
        marca=marca,
        modelo=modelo,
        descripcion=descripcion,
        precio_base=precio.quantize(Decimal("0.01")),
        estado_condicion=condicion,
    )
    db.session.add(instrumento)
    db.session.commit()
    return jsonify(instrumento.a_dict()), 201


@bp.post("/instrumentos/reservar")
@requiere_token
def reservar_instrumentos():
    """
    Marca como vendidos varios instrumentos de forma atómica (todos o ninguno).
    Lo usa el microservicio de Órdenes al confirmar una compra.
    """
    ids = _lista_ids(leer_json())
    instrumentos = (
        Instrumento.query.filter(Instrumento.id.in_(ids)).with_for_update().all()
    )
    encontrados = {i.id for i in instrumentos}
    faltantes = [i for i in ids if i not in encontrados]
    if faltantes:
        db.session.rollback()
        raise no_encontrado(_("Instrumentos inexistentes: %(ids)s", ids=faltantes))

    vendidos = [i for i in instrumentos if i.estado_venta != "disponible"]
    if vendidos:
        db.session.rollback()
        nombres = ", ".join(f"{i.marca} {i.modelo}" for i in vendidos)
        raise conflicto(_("Ya no están disponibles: %(nombres)s", nombres=nombres))

    for instrumento in instrumentos:
        instrumento.estado_venta = "vendido"
    db.session.commit()
    return jsonify([i.a_dict() for i in instrumentos])


@bp.post("/instrumentos/liberar")
@requiere_token
def liberar_instrumentos():
    """Compensación: devuelve instrumentos a 'disponible' si la compra falló."""
    ids = _lista_ids(leer_json())
    instrumentos = Instrumento.query.filter(Instrumento.id.in_(ids)).all()
    for instrumento in instrumentos:
        instrumento.estado_venta = "disponible"
    db.session.commit()
    return jsonify([i.a_dict() for i in instrumentos])


# ---------------------------------------------------------------------------
# Servicio a PROVEER para el equipo aliado (público, solo lectura)
# ---------------------------------------------------------------------------
@bp.get("/publico/instrumentos")
def api_publica_instrumentos():
    base_url = os.environ.get("PUBLIC_BASE_URL", "").rstrip("/")
    instrumentos = (
        Instrumento.query.filter_by(estado_venta="disponible")
        .order_by(Instrumento.creado_en.desc(), Instrumento.id.desc())
        .limit(50)
        .all()
    )
    datos = [
        {
            "id": i.id,
            "nombre": f"{i.marca} {i.modelo}",
            "categoria": i.categoria.nombre,
            "precio": float(i.precio_base),
            "moneda": "COP",
            "condicion": i.estado_condicion,
            "vendedor": i.vendedor.nombre,
            "url": f"{base_url}/catalogo/{i.id}/" if base_url else f"/catalogo/{i.id}/",
        }
        for i in instrumentos
    ]
    respuesta = jsonify(
        {
            "sistema": "AfinaMercado",
            "descripcion": _("Instrumentos musicales disponibles para la venta"),
            "generado_en": datetime.now(timezone.utc).isoformat(),
            "total": len(datos),
            "instrumentos": datos,
        }
    )
    respuesta.headers["Access-Control-Allow-Origin"] = "*"
    return respuesta


# ---------------------------------------------------------------------------
# Fábrica de la aplicación
# ---------------------------------------------------------------------------
def create_app(config=None):
    app = Flask(__name__)
    app.config.update(
        SQLALCHEMY_DATABASE_URI=os.environ.get("DATABASE_URL", "sqlite:///catalogo.db"),
        SQLALCHEMY_ENGINE_OPTIONS={"pool_pre_ping": True},
        SERVICE_TOKEN=os.environ.get("SERVICE_TOKEN", ""),
        JSON_SORT_KEYS=False,
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
        return jsonify({"status": "ok", "servicio": "catalogo_service"})

    return app


app = create_app()
