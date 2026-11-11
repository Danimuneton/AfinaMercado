"""Crea las tablas y carga datos de demostración antes de arrancar gunicorn."""
import os

from app import app
from models import db
from seed import sembrar_datos

with app.app_context():
    db.create_all()
    if os.environ.get("SEED_DATA", "1") == "1":
        sembrar_datos()
    print("catalogo_service: base de datos lista")
