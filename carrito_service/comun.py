"""
Utilidades internas del microservicio: errores estructurados, seguridad
entre servicios e idioma. Cada microservicio tiene su propia copia para
mantenerse independiente (no comparten código ni base de datos).
"""
import hmac
import logging
from functools import wraps

from flask import current_app, jsonify, request
from flask_babel import gettext as _
from werkzeug.exceptions import HTTPException

logger = logging.getLogger(__name__)

IDIOMAS = ["es", "en"]


def seleccionar_idioma():
    """El idioma lo decide el cliente con la cabecera Accept-Language."""
    return request.accept_languages.best_match(IDIOMAS) or "es"


class ErrorServicio(Exception):
    """Error de negocio que se traduce en una respuesta JSON estructurada."""

    def __init__(self, status, codigo, detalle, campos=None):
        super().__init__(detalle)
        self.status = status
        self.codigo = codigo
        self.detalle = detalle
        self.campos = campos

    def a_dict(self):
        cuerpo = {"error": self.codigo, "detalle": self.detalle}
        if self.campos:
            cuerpo["campos"] = self.campos
        return cuerpo


def solicitud_invalida(detalle, campos=None):
    return ErrorServicio(400, "solicitud_invalida", detalle, campos)


def no_encontrado(detalle):
    return ErrorServicio(404, "no_encontrado", detalle)


def conflicto(detalle):
    return ErrorServicio(409, "conflicto", detalle)


def leer_json():
    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        raise solicitud_invalida(_("El cuerpo de la petición debe ser un objeto JSON."))
    return data


def requiere_token(vista):
    """Solo otros servicios del sistema (que conocen SERVICE_TOKEN) pueden llamar."""

    @wraps(vista)
    def envoltura(*args, **kwargs):
        esperado = current_app.config.get("SERVICE_TOKEN") or ""
        recibido = request.headers.get("X-Service-Token", "")
        if not esperado or not hmac.compare_digest(recibido.encode(), esperado.encode()):
            return (
                jsonify({"error": "no_autorizado", "detalle": _("Token de servicio inválido o ausente.")}),
                401,
            )
        return vista(*args, **kwargs)

    return envoltura


def registrar_manejadores_error(app, db=None):
    @app.errorhandler(ErrorServicio)
    def manejar_error_servicio(error):
        return jsonify(error.a_dict()), error.status

    @app.errorhandler(HTTPException)
    def manejar_error_http(error):
        codigos = {
            400: "solicitud_invalida",
            404: "no_encontrado",
            405: "metodo_no_permitido",
            415: "tipo_no_soportado",
        }
        mensajes = {
            400: _("Solicitud inválida."),
            404: _("Recurso no encontrado."),
            405: _("Método HTTP no permitido en esta ruta."),
            415: _("El contenido debe enviarse como JSON."),
        }
        cuerpo = {
            "error": codigos.get(error.code, "error_http"),
            "detalle": mensajes.get(error.code, _("Error en la solicitud.")),
        }
        return jsonify(cuerpo), error.code

    @app.errorhandler(Exception)
    def manejar_error_interno(error):
        if db is not None:
            db.session.rollback()
        logger.exception("Error no controlado")
        return (
            jsonify({"error": "error_interno", "detalle": _("Ocurrió un error inesperado en el servicio.")}),
            500,
        )
