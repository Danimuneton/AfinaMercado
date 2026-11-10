"""Crea las tablas antes de arrancar gunicorn."""
from app import app
from models import db

with app.app_context():
    db.create_all()
    print("ordenes_service: base de datos lista")
