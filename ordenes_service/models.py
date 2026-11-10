from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

ESTADOS_ORDEN = ("creada", "pagada", "cancelada")
ESTADOS_ENVIO = ("pendiente", "en_camino", "entregado")
METODOS_PAGO = ("tarjeta", "transferencia", "pse", "nequi")


def _ahora():
    return datetime.now(timezone.utc)


class Orden(db.Model):
    __tablename__ = "ordenes"

    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, nullable=False, index=True)
    email = db.Column(db.String(254), nullable=False, default="")
    fecha = db.Column(db.DateTime(timezone=True), nullable=False, default=_ahora)
    estado = db.Column(db.String(20), nullable=False, default="creada")
    total = db.Column(db.Numeric(12, 2), nullable=False)
    direccion_envio = db.Column(db.String(255), nullable=False)
    metodo_pago = db.Column(db.String(20), nullable=False)
    transaccion_id = db.Column(db.String(64), nullable=True)
    motivo_cancelacion = db.Column(db.String(255), nullable=True)

    lineas = db.relationship("LineaOrden", backref="orden", cascade="all, delete-orphan")
    envio = db.relationship("Envio", backref="orden", uselist=False, cascade="all, delete-orphan")

    def a_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "fecha": self.fecha.isoformat() if self.fecha else None,
            "estado": self.estado,
            "total": float(self.total),
            "moneda": "COP",
            "direccion_envio": self.direccion_envio,
            "metodo_pago": self.metodo_pago,
            "transaccion_id": self.transaccion_id,
            "motivo_cancelacion": self.motivo_cancelacion,
            "lineas": [l.a_dict() for l in self.lineas],
            "envio": self.envio.a_dict() if self.envio else None,
        }


class LineaOrden(db.Model):
    __tablename__ = "lineas_orden"

    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("ordenes.id"), nullable=False)
    # Copia de los datos del instrumento al momento de la compra (sin acoplarse a la BD de Catálogo).
    instrumento_id = db.Column(db.Integer, nullable=False)
    marca = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    categoria = db.Column(db.String(100), nullable=False)
    vendedor = db.Column(db.String(150), nullable=False)
    precio_final = db.Column(db.Numeric(12, 2), nullable=False)

    def a_dict(self):
        return {
            "instrumento_id": self.instrumento_id,
            "instrumento": f"{self.marca} {self.modelo}",
            "categoria": self.categoria,
            "vendedor": self.vendedor,
            "precio_final": float(self.precio_final),
        }


class Envio(db.Model):
    __tablename__ = "envios"

    id = db.Column(db.Integer, primary_key=True)
    orden_id = db.Column(db.Integer, db.ForeignKey("ordenes.id"), unique=True, nullable=False)
    direccion = db.Column(db.String(255), nullable=False)
    estado = db.Column(db.String(20), nullable=False, default="pendiente")
    asegurado = db.Column(db.Boolean, nullable=False, default=False)

    def a_dict(self):
        return {"direccion": self.direccion, "estado": self.estado, "asegurado": self.asegurado}
