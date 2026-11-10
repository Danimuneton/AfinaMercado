# Django: interfaz web (consume los microservicios) + API legacy /api/v1/
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# gettext es necesario para compilar las traducciones (.po -> .mo)
RUN apt-get update \
    && apt-get install -y --no-install-recommends gettext \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

# Traducciones y archivos estáticos se generan en la construcción de la imagen.
RUN DJANGO_SECRET_KEY=solo-para-build python manage.py compilemessages \
    && DJANGO_SECRET_KEY=solo-para-build DJANGO_DEBUG=False python manage.py collectstatic --noinput \
    && sed -i 's/\r$//' docker/django-entrypoint.sh

# No ejecutar la aplicación como root
RUN useradd --create-home app && chown -R app /app
USER app

EXPOSE 8000

CMD ["sh", "docker/django-entrypoint.sh"]
