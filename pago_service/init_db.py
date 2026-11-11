"""Crea las tablas antes de arrancar gunicorn."""
from app import app, db

with app.app_context():
    db.create_all()
    print("pago_service: base de datos lista")
