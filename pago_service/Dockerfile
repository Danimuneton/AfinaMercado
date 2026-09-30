# Dockerfile independiente del microservicio de Pagos (Flask)
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt

COPY . /app/

EXPOSE 5000

# Servidor de aplicaciones (gunicorn) apuntando a la app Flask
CMD ["gunicorn", "app:app", "--bind", "0.0.0.0:5000", "--workers", "2"]
