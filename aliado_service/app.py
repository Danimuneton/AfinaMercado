"""
Servicio aliado SIMULADO - "Academia Armonía".

El curso pide consumir el servicio de un equipo aliado. Mientras no haya un
equipo asignado, este contenedor hace el papel del sistema externo: expone un
endpoint JSON propio (con un formato distinto al de AfinaMercado) que Django
consume a través de AliadoHttpAdapter.

Para usar el servicio de un equipo real basta con poner su URL en
ALIADO_API_URL del archivo .env; no hay que cambiar código.
"""
from datetime import datetime, timezone

from flask import Flask, jsonify

app = Flask(__name__)
app.json.ensure_ascii = False
app.json.sort_keys = False

CLASES = [
    {"codigo": "GUI-101", "curso": "Guitarra acústica", "instrumento": "Guitarra", "nivel": "Principiante", "horario": "Lunes y miércoles 6:00 p. m.", "precio_mensual": 180000, "cupos": 6},
    {"codigo": "GUI-201", "curso": "Guitarra eléctrica", "instrumento": "Guitarra", "nivel": "Intermedio", "horario": "Martes 7:00 p. m.", "precio_mensual": 220000, "cupos": 4},
    {"codigo": "BAJ-101", "curso": "Bajo eléctrico", "instrumento": "Bajo", "nivel": "Principiante", "horario": "Jueves 5:00 p. m.", "precio_mensual": 200000, "cupos": 5},
    {"codigo": "BAT-101", "curso": "Batería", "instrumento": "Batería", "nivel": "Principiante", "horario": "Sábados 9:00 a. m.", "precio_mensual": 240000, "cupos": 3},
    {"codigo": "PIA-101", "curso": "Piano", "instrumento": "Piano", "nivel": "Principiante", "horario": "Lunes 4:00 p. m.", "precio_mensual": 230000, "cupos": 0},
    {"codigo": "SAX-201", "curso": "Saxofón", "instrumento": "Saxofón", "nivel": "Intermedio", "horario": "Viernes 6:00 p. m.", "precio_mensual": 260000, "cupos": 2},
]


@app.get("/api/clases")
def clases():
    return jsonify(
        {
            "proveedor": "Academia Armonía (servicio aliado simulado)",
            "actualizado": datetime.now(timezone.utc).isoformat(),
            "clases": CLASES,
        }
    )


@app.get("/health")
def health():
    return jsonify({"status": "ok", "servicio": "aliado_simulado"})


@app.errorhandler(404)
def no_encontrado(_error):
    return jsonify({"error": "no_encontrado"}), 404
