# SmartLuben API

Backend para gestión de exhibición y reposición de productos en mostrador de confitería.

## Tecnologías

- **FastAPI** - Framework web moderno y rápido
- **PostgreSQL 16** - Base de datos relacional
- **SQLAlchemy 2.0** - ORM asíncrono
- **Pydantic v2** - Validación y serialización
- **Alembic** - Migraciones de base de datos
- **Docker** - Contenedores

## Estructura del Proyecto

```
backend/
├── app/
│   ├── main.py              # Aplicación FastAPI
│   ├── config.py            # Configuración
│   ├── database.py          # Conexión a BD
│   ├── models/              # Modelos SQLAlchemy
│   │   ├── __init__.py
│   ├── schemas/             # Schemas Pydantic
│   │   ├── __init__.py
│   │   ├── producto.py
│   │   ├── espacio.py
│   │   ├── movimiento.py
│   │   ├── dashboard.py
│   ├── routers/             # Endpoints API
│   │   ├── __init__.py
│   │   ├── productos.py
│   │   ├── espacios.py
│   │   ├── movimientos.py
│   │   ├── dashboard.py
│   ├── services/            # Lógica de negocio
│   │   ├── __init__.py
├── tests/                   # Tests
├── alembic/                 # Migraciones
├── scripts/                 # Scripts de utilidad
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
├── alembic.ini
└── .env.example
```

## Requisitos

- Docker y Docker Compose
- O bien: Python 3.12+, PostgreSQL 16

## Variables de Entorno

Copiar `.env.example` a `.env` y ajustar:

```bash
cp .env.example .env
```

| Variable | Descripción | Default |
|----------|-------------|---------|
| `DATABASE_URL` | URL de conexión a PostgreSQL | `postgresql+asyncpg://postgres:postgres@db:5432/smart_luben` |
| `DEBUG` | Modo debug | `false` |
| `CORS_ORIGINS` | Orígenes permitidos CORS | `["*"]` |

## Levantar con Docker (Recomendado)

```bash
cd backend
docker-compose up --build
```

La API estará disponible en:
- **API**: http://localhost:8000
- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
- **Health Check**: http://localhost:8000/health

## Levantar en Desarrollo Local

```bash
cd backend

# Crear entorno virtual
python -m venv venv
source venv/bin/activate  # Linux/Mac
# venv\Scripts\activate  # Windows

# Instalar dependencias
pip install -r requirements.txt

# Configurar variables de entorno
cp .env.example .env
# Editar .env con tu DATABASE_URL local

# Ejecutar migraciones
alembic upgrade head

# Ejecutar seed (opcional)
python scripts/seed.py

# Iniciar servidor
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## Migraciones con Alembic

```bash
# Crear nueva migración (tras cambios en modelos)
alembic revision --autogenerate -m "descripcion"

# Aplicar migraciones
alembic upgrade head

# Ver historial
alembic history

# Revertir última migración
alembic downgrade -1
```

## Seed de Datos Iniciales

```bash
python scripts/seed.py
```

Crea:
- 8 espacios (E01-E08) con ubicaciones de ejemplo
- 6 productos de ejemplo

## Tests

```bash
# Con base de datos de test (requiere PostgreSQL corriendo en localhost:5432 con BD smart_luben_test)
pytest tests/ -v

# O con docker-compose (levanta BD de test aparte)
docker-compose -f docker-compose.test.yml up --build --abort-on-container-exit
```

## Endpoints

### Productos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/productos` | Crear producto |
| GET | `/api/productos` | Listar productos (`?activo=true/false`) |
| GET | `/api/productos/{id}` | Obtener producto |
| PUT | `/api/productos/{id}` | Actualizar producto |
| DELETE | `/api/productos/{id}` | Soft delete (activo=false) |

### Espacios

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| POST | `/api/espacios` | Crear espacio |
| GET | `/api/espacios` | Listar espacios (con producto actual) |
| GET | `/api/espacios/{id}` | Obtener espacio |
| PUT | `/api/espacios/{id}` | Actualizar espacio |
| DELETE | `/api/espacios/{id}` | Eliminar (solo si libre) |
| POST | `/api/espacios/{id}/reponer` | Reponer espacio libre |
| POST | `/api/espacios/{id}/liberar` | Liberar espacio ocupado |

### Movimientos

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/movimientos` | Historial con filtros |
| GET | `/api/espacios/{id}/movimientos` | Movimientos de un espacio |

**Filtros para `/api/movimientos`:**
- `espacio_id`
- `producto_id`
- `tipo` (reposicion/salida)
- `desde` (ISO 8601)
- `hasta` (ISO 8601)
- `skip`, `limit` (paginación)

### Dashboard

| Método | Endpoint | Descripción |
|--------|----------|-------------|
| GET | `/api/dashboard/resumen` | Resumen general |

## Ejemplos cURL

### Crear producto
```bash
curl -X POST http://localhost:8000/api/productos \
  -H "Content-Type: application/json" \
  -d '{"nombre": "Empanada de carne", "categoria": "Salados", "imagen_url": "https://ejemplo.com/img.jpg"}'
```

### Listar productos activos
```bash
curl http://localhost:8000/api/productos?activo=true
```

### Crear espacio
```bash
curl -X POST http://localhost:8000/api/espacios \
  -H "Content-Type: application/json" \
  -d '{"codigo": "E09", "ubicacion": "Fila 3, Col 1"}'
```

### Reponer espacio
```bash
curl -X POST http://localhost:8000/api/espacios/1/reponer \
  -H "Content-Type: application/json" \
  -d '{"producto_id": 1}'
```

### Liberar espacio
```bash
curl -X POST http://localhost:8000/api/espacios/1/liberar
```

### Ver historial de movimientos
```bash
curl "http://localhost:8000/api/movimientos?espacio_id=1&tipo=reposicion"
```

### Ver dashboard
```bash
curl http://localhost:8000/api/dashboard/resumen
```

## Reglas de Negocio

1. **Un espacio = Un producto** - Un espacio solo puede tener un producto a la vez
2. **Reponer** - Requiere espacio LIBRE + producto ACTIVO → Cambia a OCUPADO + registra movimiento "reposicion"
3. **Liberar** - Requiere espacio OCUPADO → Cambia a LIBRE + limpia producto + registra movimiento "salida"
4. **Soft delete** - Productos se desactivan, no se eliminan
5. **Eliminar espacio** - Solo si está LIBRE

## Códigos de Error

| Código | Descripción |
|--------|-------------|
| 400 | Error de validación / Regla de negocio (ej. reponer espacio ocupado) |
| 404 | Recurso no encontrado |
| 409 | Conflicto (duplicado: nombre producto / código espacio) |

## Licencia

MIT