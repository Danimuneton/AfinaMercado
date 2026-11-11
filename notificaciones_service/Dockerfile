# Worker asíncrono de notificaciones y reportes (Celery + Redis)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Compila las traducciones (gettext .po -> .mo)
RUN pybabel compile -d translations

# Celery no debe correr como root
RUN useradd --create-home worker
USER worker

CMD ["celery", "-A", "worker", "worker", "--loglevel=info", "--concurrency=2"]
