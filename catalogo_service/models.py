from datetime import datetime, timezone

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()

CONDICIONES = ("excelente", "bueno", "regular")
ESTADOS_VENTA = ("disponible", "vendido")


def _ahora():
    return datetime.now(timezone.utc)


class Vendedor(db.Model):
    __tablename__ = "vendedores"

    id = db.Column(db.Integer, primary_key=True)
    # Id del usuario en el sistema de autenticación (Django). Opcional para tiendas.
    usuario_id = db.Column(db.Integer, unique=True, nullable=True)
    nombre = db.Column(db.String(150), nullable=False)
    contacto = db.Column(db.String(150), nullable=False, default="")

    def a_dict(self):
        return {
            "id": self.id,
            "usuario_id": self.usuario_id,
            "nombre": self.nombre,
            "contacto": self.contacto,
        }


class Categoria(db.Model):
    __tablename__ = "categorias"

    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(100), unique=True, nullable=False)

    def a_dict(self):
        return {"id": self.id, "nombre": self.nombre}


class Instrumento(db.Model):
    __tablename__ = "instrumentos"

    id = db.Column(db.Integer, primary_key=True)
    vendedor_id = db.Column(db.Integer, db.ForeignKey("vendedores.id"), nullable=False)
    categoria_id = db.Column(db.Integer, db.ForeignKey("categorias.id"), nullable=False)
    marca = db.Column(db.String(100), nullable=False)
    modelo = db.Column(db.String(100), nullable=False)
    descripcion = db.Column(db.Text, nullable=False, default="")
    precio_base = db.Column(db.Numeric(12, 2), nullable=False)
    estado_condicion = db.Column(db.String(20), nullable=False)
    estado_venta = db.Column(db.String(20), nullable=False, default="disponible")
    creado_en = db.Column(db.DateTime(timezone=True), nullable=False, default=_ahora)

    vendedor = db.relationship("Vendedor", backref="instrumentos")
    categoria = db.relationship("Categoria", backref="instrumentos")

    def a_dict(self):
        return {
            "id": self.id,
            "marca": self.marca,
            "modelo": self.modelo,
            "descripcion": self.descripcion,
            "precio_base": float(self.precio_base),
            "moneda": "COP",
            "estado_condicion": self.estado_condicion,
            "estado_venta": self.estado_venta,
            "categoria": self.categoria.a_dict(),
            "vendedor": self.vendedor.a_dict(),
            "creado_en": self.creado_en.isoformat() if self.creado_en else None,
        }
