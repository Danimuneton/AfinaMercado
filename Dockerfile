# Dockerfile del monolito Django (AfinaMercado)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Dependencias
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

# Código fuente
COPY . /app/

EXPOSE 8000

# Migraciones + servidor de aplicaciones (gunicorn)
CMD ["sh", "-c", "python manage.py migrate --noinput && gunicorn afinamercado_project.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
