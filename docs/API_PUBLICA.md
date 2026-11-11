# API pública de AfinaMercado (servicio a proveer al equipo aliado)

Endpoint JSON de solo lectura con los instrumentos musicales disponibles para la venta.
Lo expone el **microservicio de Catálogo (Flask)** a través del API Gateway (Nginx).

| | |
|---|---|
| **Método** | `GET` |
| **URL** | `http://<IP_ELASTICA>/api/v2/catalogo/publico/instrumentos` |
| **Autenticación** | No requiere |
| **Formato** | JSON (UTF-8) |
| **CORS** | `Access-Control-Allow-Origin: *` (se puede consumir desde otro dominio) |
| **Idioma** | Cabecera `Accept-Language: es` o `en` (afecta el campo `descripcion`) |
| **Límite** | 50 instrumentos más recientes. Nginx limita a 20 peticiones/segundo por IP |

## Ejemplo de respuesta (`200 OK`)

```json
{
  "sistema": "AfinaMercado",
  "descripcion": "Instrumentos musicales disponibles para la venta",
  "generado_en": "2026-11-10T22:18:13.699744+00:00",
  "total": 2,
  "instrumentos": [
    {
      "id": 8,
      "nombre": "Gibson Les Paul Studio",
      "categoria": "Guitarras",
      "precio": 7900000.0,
      "moneda": "COP",
      "condicion": "excelente",
      "vendedor": "Música Medellín",
      "url": "http://<IP_ELASTICA>/catalogo/8/"
    },
    {
      "id": 2,
      "nombre": "Yamaha C40",
      "categoria": "Guitarras",
      "precio": 450000.0,
      "moneda": "COP",
      "condicion": "bueno",
      "vendedor": "Tienda La Clave",
      "url": "http://<IP_ELASTICA>/catalogo/2/"
    }
  ]
}
```

## Campos

| Campo | Tipo | Descripción |
|---|---|---|
| `id` | entero | Identificador del instrumento |
| `nombre` | texto | Marca y modelo |
| `categoria` | texto | Categoría del instrumento |
| `precio` | número | Precio de venta |
| `moneda` | texto | Siempre `COP` |
| `condicion` | texto | `excelente`, `bueno` o `regular` |
| `vendedor` | texto | Nombre del vendedor o tienda |
| `url` | texto | Enlace a la página del instrumento en AfinaMercado |

## Errores

Si el microservicio no está disponible, el gateway responde `503` con un JSON estructurado:

```json
{ "error": "servicio_no_disponible", "detalle": "El microservicio no está disponible en este momento. Intenta de nuevo en unos segundos." }
```

## Prueba rápida

```powershell
Invoke-RestMethod -Uri "http://<IP_ELASTICA>/api/v2/catalogo/publico/instrumentos"
```
