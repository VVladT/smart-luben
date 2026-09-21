# Smart Luben

## Desarrollo local

### Requisitos

- Python 3.12+
- Node.js
- Docker
- Docker Compose

### 1. Configuración

cp .env.example .env

### 2. Instalar dependencias

make install

### 3. Levantar PostgreSQL

make db

### 4. Ejecutar migraciones

make migrate

### 5. Cargar datos iniciales

make seed

### 6. Levantar backend

make backend

Backend: http://localhost:8000

### 7. Levantar frontend

make frontend

Frontend: http://localhost:4200
