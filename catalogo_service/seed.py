"""Datos de demostración para que el catálogo no arranque vacío."""
from decimal import Decimal

from models import Categoria, Instrumento, Vendedor, db

CATEGORIAS = ["Guitarras", "Bajos", "Baterías y percusión", "Teclados y pianos", "Vientos"]

VENDEDORES = [
    ("Tienda La Clave", "ventas@laclave.co"),
    ("Música Medellín", "contacto@musicamedellin.co"),
]

INSTRUMENTOS = [
    # (vendedor, categoría, marca, modelo, precio COP, condición, descripción)
    (0, 0, "Fender", "Stratocaster Player", "4200000", "excelente", "Guitarra eléctrica, mástil de arce."),
    (0, 0, "Yamaha", "C40", "450000", "bueno", "Guitarra clásica ideal para principiantes."),
    (1, 1, "Ibanez", "SR300E", "2100000", "excelente", "Bajo activo de 4 cuerdas."),
    (1, 2, "Pearl", "Roadshow", "2800000", "regular", "Batería completa de 5 piezas con platillos."),
    (0, 3, "Casio", "CT-S300", "780000", "excelente", "Teclado de 61 teclas sensibles."),
    (1, 3, "Roland", "FP-30X", "3500000", "bueno", "Piano digital de 88 teclas."),
    (0, 4, "Yamaha", "YAS-280", "5200000", "bueno", "Saxofón alto para estudiante."),
    (1, 0, "Gibson", "Les Paul Studio", "7900000", "excelente", "Guitarra eléctrica con estuche."),
]


def sembrar_datos():
    if Categoria.query.first() is not None:
        return
    categorias = [Categoria(nombre=n) for n in CATEGORIAS]
    vendedores = [Vendedor(nombre=n, contacto=c) for n, c in VENDEDORES]
    db.session.add_all(categorias + vendedores)
    db.session.flush()
    for v, c, marca, modelo, precio, condicion, descripcion in INSTRUMENTOS:
        db.session.add(
            Instrumento(
                vendedor=vendedores[v],
                categoria=categorias[c],
                marca=marca,
                modelo=modelo,
                precio_base=Decimal(precio),
                estado_condicion=condicion,
                descripcion=descripcion,
            )
        )
    db.session.commit()
