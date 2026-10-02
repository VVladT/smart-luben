from typing import Optional

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, ConfigDict


router = APIRouter(prefix="/uploads", tags=["uploads"])

storage_router = APIRouter(prefix="/storage", tags=["storage"])


class PresignRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    tipo: str  # 'modelo' | 'imagen'
    filename: str
    content_type: str
    size: Optional[int] = None


class PresignResponse(BaseModel):
    upload_url: str
    public_url: str
    bucket: str
    object_path: str


@router.post(
    "/presign",
    response_model=PresignResponse,
    summary="URL presignada de subida",
    description="Valida el archivo y devuelve URL de subida directa a MinIO + URL pública final.",
)
async def presign_upload(request: PresignRequest):
    from app.services.storage import (
        ensure_buckets,
        object_name,
        presigned_put,
        public_url,
        validar_archivo,
    )

    try:
        validar_archivo(request.tipo, request.filename, request.content_type, request.size)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    try:
        ensure_buckets()
        obj = object_name(request.tipo, request.filename)
        return PresignResponse(
            upload_url=presigned_put("smart-luben", obj),
            public_url=public_url("smart-luben", obj),
            bucket="smart-luben",
            object_path=obj,
        )
    except Exception as e:
        raise HTTPException(status_code=502, detail=f"S3 no disponible: {e}")


@storage_router.get(
    "/{bucket}/{object_path:path}",
    summary="Leer objeto",
    description="Sirve los bytes con la misma origen (sin CORS). "
    "El browser/AR lo cachea; la subida sigue directa por presigned PUT.",
)
async def leer_objeto(bucket: str, object_path: str, request: Request):
    from app.services.storage import BUCKETS, get_client

    if bucket not in BUCKETS or ".." in object_path:
        raise HTTPException(status_code=404, detail="No encontrado")

    # Soporte Range (el GLTFLoader y navegadores lo agradecen)
    rango = request.headers.get("range")
    offset = 0
    fin = None
    if rango and rango.startswith("bytes="):
        try:
            partes = rango[6:].split("-")
            offset = int(partes[0] or 0)
            fin = int(partes[1]) if len(partes) > 1 and partes[1] else None
        except ValueError:
            offset, fin = 0, None

    try:
        client = get_client()
        stat = client.stat_object(bucket, object_path)
        total = stat.size
        if fin is None or fin >= total:
            fin = total - 1
        if offset >= total:
            raise HTTPException(status_code=416, detail="Rango inválido")
        respuesta = client.get_object(bucket, object_path, offset=offset, length=fin - offset + 1)
    except HTTPException:
        raise
    except Exception as e:
        if "NoSuchKey" in type(e).__name__ or "NoSuchKey" in str(e):
            raise HTTPException(status_code=404, detail="No encontrado")
        raise HTTPException(status_code=502, detail=f"S3 no disponible: {e}")

    media = _media_type(object_path)

    async def generador():
        try:
            for chunk in respuesta.stream(64 * 1024):
                yield chunk
        finally:
            respuesta.close()
            respuesta.release_conn()

    headers = {
        "Accept-Ranges": "bytes",
        "Content-Length": str(fin - offset + 1),
        "Cache-Control": "public, max-age=3600",
    }
    status = 206 if rango else 200
    if rango:
        headers["Content-Range"] = f"bytes {offset}-{fin}/{total}"
    return StreamingResponse(generador(), media_type=media, status_code=status, headers=headers)


def _media_type(object_path: str) -> str:
    nombre = object_path.lower()
    if nombre.endswith(".glb"):
        return "model/gltf-binary"
    if nombre.endswith(".png"):
        return "image/png"
    if nombre.endswith(".webp"):
        return "image/webp"
    if nombre.endswith((".jpg", ".jpeg")):
        return "image/jpeg"
    return "application/octet-stream"
