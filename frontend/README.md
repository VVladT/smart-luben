# SmartLuben Frontend

Frontend Angular 22 para el sistema de gestión de exhibición y reposición de productos en mostrador de confitería.

## Tecnologías

- **Angular 22** - Standalone components, signals, httpResource
- **TailwindCSS 4** - Estilos utilitarios
- **Angular Material** - Componentes UI (tablas, diálogos, formularios)
- **RxJS** - Programación reactiva
- **TypeScript** - Tipado estático

## Estructura del proyecto

```
src/
├── app/
│   ├── core/
│   │   ├── api/
│   │   │   ├── api-client.ts           # Configuración HTTP, interceptores
│   │   │   └── generated/
│   │   │       └── models.ts           # Tipos generados desde openapi.json
│   │   └── services/
│   │       ├── productos.service.ts    # API de productos
│   │       ├── espacios.service.ts     # API de espacios
│   │       ├── movimientos.service.ts  # API de movimientos
│   │       └── dashboard.service.ts    # API de dashboard
│   ├── features/
│   │   ├── mostrador/
│   │   │   ├── mostrador.page.ts       # Vista principal del mostrador
│   │   │   ├── espacio-card.component.ts
│   │   │   ├── modal-reponer.component.ts
│   │   │   └── modal-confirmar.component.ts
│   │   ├── productos/
│   │   │   ├── productos.page.ts       # Gestión de productos
│   │   │   └── producto-form.component.ts
│   │   ├── movimientos/
│   │   │   └── movimientos.page.ts     # Historial de movimientos
│   │   └── dashboard/
│   │       └── dashboard.page.ts       # Dashboard con métricas
│   ├── shared/
│   │   ├── navbar.component.ts         # Navegación principal
│   │   ├── loading-spinner.component.ts
│   │   └── error-message.component.ts
│   ├── app.routes.ts                   # Rutas con lazy loading
│   ├── app.config.ts                   # Configuración de la app
│   └── app.ts                          # Componente raíz
├── environments/
│   ├── environment.ts                  # Config desarrollo
│   └── environment.prod.ts             # Config producción
├── styles.scss                         # Estilos globales + Tailwind
└── main.ts                             # Bootstrap
```

## Requisitos

- Node.js 20+
- npm 10+
- Backend FastAPI corriendo en `http://localhost:8000`

## Instalación

```bash
cd frontend
npm install
```

## Desarrollo

```bash
# Levantar servidor de desarrollo
npm start

# La app estará en http://localhost:4200
# El proxy redirige /api/* a http://localhost:8000/api
```

## Generar tipos desde OpenAPI

```bash
# Regenerar types/interfaces desde openapi.json
npm run generate:types
```

## Build para producción

```bash
npm run build
# Salida en dist/smart-luben/browser
```

## Docker

```bash
# Build imagen
npm run docker:build

# Run contenedor
npm run docker:run

# O usar docker-compose
npm run docker:compose:up
npm run docker:compose:down
```

## Variables de entorno

Copiar `.env.example` a `.env` y ajustar:

```env
API_URL=http://localhost:8000/api
```

## Pantallas

1. **Dashboard** (`/dashboard`) - Métricas y accesos rápidos
2. **Mostrador** (`/mostrador`) - Grid de espacios con acciones reponer/liberar
3. **Productos** (`/productos`) - CRUD de productos con filtro activo/inactivo
4. **Historial** (`/movimientos`) - Movimientos con filtros y paginación

## Reglas de negocio implementadas

- Un espacio solo puede tener UN producto a la vez
- Reponer: requiere espacio LIBRE + producto ACTIVO
- Liberar: requiere espacio OCUPADO
- Soft delete de productos (desactivar)
- Auto-refresh cada 10s en el mostrador
- Manejo de errores del backend (campo `detail`)

## Scripts disponibles

| Comando | Descripción |
|---------|-------------|
| `npm start` | Servidor desarrollo |
| `npm run build` | Build producción |
| `npm run test` | Tests unitarios |
| `npm run lint` | Linter |
| `npm run generate:types` | Regenerar tipos TypeScript |
| `npm run docker:build` | Build imagen Docker |
| `npm run docker:compose:up` | Levantar con docker-compose |