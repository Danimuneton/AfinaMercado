# Microservicio de Órdenes y Envíos (Flask)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Compila las traducciones (gettext .po -> .mo)
RUN pybabel compile -d translations

EXPOSE 5000

CMD ["sh", "-c", "python init_db.py && gunicorn app:app --bind 0.0.0.0:5000 --workers 2 --timeout 60"]
