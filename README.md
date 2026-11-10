# AfinaMercado: marketplace de instrumentos musicales

Proyecto de la materia **Arquitectura de Software 2026** (EAFIT).

Ecosistema híbrido construido con el **Strangler Pattern**: Django mantiene la interfaz web y la
autenticación, y la lógica de negocio vive en microservicios Flask independientes, detrás de Nginx
como API Gateway, con tareas asíncronas en Celery + Redis y soporte bilingüe (español / inglés).

Documentación detallada en la **Wiki** del repositorio y en [`docs/`](docs/):

- [Entrega 2: Microservicios, integración y resiliencia](docs/wiki/Entrega-2-Microservicios-Integracion-y-Resiliencia.md) (arquitectura, matriz de decisión, diagramas)
- [Taller 2: Strangler Pattern](docs/wiki/Migracion-a-Microservicios-Strangler-Pattern.md)
- [Despliegue en AWS Academy (EC2)](docs/DESPLIEGUE_AWS.md)
- [API pública para el equipo aliado](docs/API_PUBLICA.md)

## Arquitectura

```
                       ┌──────────────────────── Docker Compose (AWS EC2) ───────────────────────┐
Usuario ── HTTP :80 ──▶│ Nginx (API Gateway)                                                     │
                       │   ├── /, /admin/, /api/v1/ ─▶ Django (web, auth, i18n, Adapter) ─┐      │
                       │   ├── /api/v2/catalogo/    ─▶ Flask catalogo_service             │      │
                       │   ├── /api/v2/carrito/     ─▶ Flask carrito_service              ├─▶ PostgreSQL
                       │   ├── /api/v2/ordenes/     ─▶ Flask ordenes_service ──┐          │   (1 BD por servicio)
                       │   └── /api/v2/pagos/       ─▶ Flask pago_service      │          │      │
                       │                                                       ▼          │      │
                       │                         Redis (broker) ─▶ Celery notificaciones_worker  │
                       └──────────────────────────────────────────────────────────────────────────┘
```

| Carpeta | Servicio | Descripción |
|---|---|---|
| `web/` + `afinamercado_project/` | Django | Interfaz web, autenticación, i18n, integraciones (divisas y aliado con patrón Adapter) |
| `ordenes/` | Django | API legacy `/api/v1/` (se conserva por compatibilidad) |
| `catalogo_service/` | Flask | Vendedores, categorías, instrumentos, API pública |
| `carrito_service/` | Flask | Carrito de compras |
| `ordenes_service/` | Flask | Órdenes y envíos (Builder), coordinación de la compra |
| `pago_service/` | Flask | Pagos |
| `notificaciones_service/` | Celery | Notificaciones (Factory) y reportes asíncronos |
| `nginx/` | Nginx | Configuración del API Gateway |
| `locale/` | gettext | Traducciones de Django (es / en) |

## Ejecutar en tu PC (Windows PowerShell)

Requisito: Docker Desktop abierto.

```powershell
Copy-Item .env.example .env
# Edita .env y cambia las claves (DJANGO_SECRET_KEY, POSTGRES_PASSWORD, SERVICE_TOKEN, DJANGO_SUPERUSER_PASSWORD)
docker compose up -d --build
Start-Process "http://localhost:8080/"
```

- Interfaz web: `http://localhost:8080/`
- Administración: `http://localhost:8080/admin/` (usuario `DJANGO_SUPERUSER_USERNAME` del `.env`)
- Índice del gateway: `http://localhost:8080/api/v2/`
- API pública: `http://localhost:8080/api/v2/catalogo/publico/instrumentos`

Si antes levantaste la versión del Taller 2, borra el volumen viejo de la base de datos una vez
(se pierden esos datos de prueba): `docker compose down -v`.

## Endpoints principales

| Método | Ruta | Servicio |
|---|---|---|
| GET | `/api/v2/catalogo/instrumentos?q=&categoria_id=` | Catálogo |
| GET | `/api/v2/catalogo/instrumentos/<id>` | Catálogo |
| GET | `/api/v2/catalogo/categorias` | Catálogo |
| GET | `/api/v2/catalogo/publico/instrumentos` | Catálogo (público, para el aliado) |
| GET / POST / DELETE | `/api/v2/carrito/`, `/api/v2/carrito/items` | Carrito (token interno) |
| GET / POST | `/api/v2/ordenes/` | Órdenes (token interno) |
| POST / GET | `/api/v2/pagos/` | Pagos |
| GET | `/api/v1/instrumentos/` | Django (legacy) |

Los endpoints marcados con *token interno* exigen la cabecera `X-Service-Token`. Los llama Django
en nombre del usuario que inició sesión.
