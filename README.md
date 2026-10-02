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

## Objetos 3D e imágenes (Garage S3)

Los modelos `.glb` e imágenes se guardan en Garage (S3-compatible).
La API firma subidas (presigned PUT) y redirige lecturas
(`GET /api/storage/...` → URL presignada). Sin S3 la API igual arranca.

### Primera vez por entorno

```bash
# 1. Secretos del nodo (una vez, conservarlos siempre)
openssl rand -hex 32        # -> rpc_secret (docker/garage.toml)
openssl rand -base64 32     # -> admin_token (docker/garage.toml)

# 2. Config desde plantilla
cp docker/garage.toml.example docker/garage.toml
# editar rpc_secret, admin_token, metrics_token
# En el VPS el archivo real vive JUNTO al .env (fuera de git) y el pipeline
# lo restaura solo (../garage.toml -> docker/garage.toml), igual que el .env.

# 3. Clave S3 (debe empezar con GK) y secreto en .env
# S3_ACCESS_KEY=GK... / S3_SECRET_KEY=...

# 4. Levantar y cargar modelos por defecto
docker compose up -d garage
docker compose run --rm backend python scripts/upload_default_models.py
```

> El bucket/key se crean solos (`--single-node --default-bucket`), pero hay
> que otorgar permisos una vez (la key por defecto viene sin grants):
> ```bash
> KEY=$(docker exec smart-luben-garage-dev /garage key list 2>/dev/null | awk '/^GK/{print $1}')
> docker exec smart-luben-garage-dev /garage bucket allow --read --write --owner smart-luben --key "$KEY"
> ```

Deudas técnicas: targets AR estáticos en `ar/assets`, pulido visual del
formulario de subida.
