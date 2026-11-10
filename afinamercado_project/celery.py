"""
Cliente Celery de Django. Django no ejecuta tareas: solo las publica en Redis
para que las procese el worker (notificaciones_service) y consulta su estado.
"""
from celery import Celery
from django.conf import settings

celery_app = Celery("afinamercado_web")
celery_app.conf.update(
    broker_url=settings.CELERY_BROKER_URL,
    result_backend=settings.CELERY_RESULT_BACKEND,
    task_serializer="json",
    result_serializer="json",
    accept_content=["json"],
    # Fallar rápido si Redis está caído (la página muestra un mensaje en vez de colgarse).
    broker_connection_timeout=2,
    broker_connection_retry_on_startup=False,
    broker_transport_options={
        "max_retries": 1,
        "interval_start": 0,
        "interval_step": 0.5,
        "interval_max": 0.5,
    },
    redis_socket_connect_timeout=2,
    redis_socket_timeout=2,
)
