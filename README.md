# AfinaMercado — Marketplace de Instrumentos

Proyecto de la materia **Arquitectura de Software 2026**.

## Taller 02 — Patrón Estrangulador (Strangler Pattern)

Migración híbrida de monolito a microservicios. Se extrajo el **procesamiento de
pagos** del monolito Django a un microservicio independiente en **Flask**, orquestando
el tráfico con **Nginx** y **Docker**.

La justificación completa (matriz de decisión + diagrama) está en:
[`docs/wiki/Migracion-a-Microservicios-Strangler-Pattern.md`](docs/wiki/Migracion-a-Microservicios-Strangler-Pattern.md)
(contenido listo para copiar a la Wiki del repositorio).

## Arquitectura

```
Cliente ──> Nginx (:8080)
              ├── /api/v1/…        ──> Django (monolito)      ──> PostgreSQL
              └── /api/v2/pagos/   ──> Flask (microservicio de pagos)
```

- **Monolito Django** (`ordenes/`): catálogo, vendedores, categorías, carrito y órdenes.
- **Microservicio Flask** (`pago_service/`): procesa pagos y responde JSON.
- **Nginx** (`nginx/nginx.conf`): bifurca el tráfico por URL.
- **PostgreSQL**: base de datos del monolito.

## Ejecución con Docker

```bash
docker compose up --build
```

Todo queda accesible en `http://localhost:8080`.

### Endpoints principales

| Método | Ruta                         | Servicio |
|--------|------------------------------|----------|
| GET    | `/api/v1/instrumentos/`      | Django   |
| POST   | `/api/v1/instrumentos/`      | Django   |
| GET    | `/api/v1/vendedores/`        | Django   |
| GET    | `/api/v1/categorias/`        | Django   |
| GET    | `/api/v1/carrito/`           | Django   |
| POST   | `/api/v1/carrito/items/`     | Django   |
| GET    | `/api/v1/ordenes/`           | Django   |
| POST   | `/api/v1/crear-orden/`       | Django (delega el pago a Flask) |
| POST   | `/api/v2/pagos/`             | Flask    |

## Ejecución local sin Docker (solo Django)

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

Sin la variable `DB_ENGINE=postgres`, Django usa SQLite local.
