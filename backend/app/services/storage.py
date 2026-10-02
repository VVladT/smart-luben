"""S3 compatible (Garage): buckets, URLs presignadas y redirects de lectura.

Lectura pública: NO hay buckets públicos; el backend redirige
GET /api/storage/{bucket}/{path} -> URL presignada de 10 min.
Así funciona contra cualquier S3 sin configurar policies/website.
"""

from minio import Minio

from app.config import settings


BUCKETS = ("smart-luben",)

# Validación por tipo
REGLAS = {
    "modelo": {
        "prefijo": "modelos/",
        "extensiones": (".glb",),
        "content_types": ("model/gltf-binary", "application/octet-stream"),
        "max_bytes": 50 * 1024 * 1024,
    },
    "imagen": {
        "prefijo": "imagenes/",
        "extensiones": (".jpg", ".jpeg", ".png", ".webp"),
        "content_types": ("image/jpeg", "image/png", "image/webp"),
        "max_bytes": 5 * 1024 * 1024,
    },
}


def _endpoint_sin_esquema(url: str) -> str:
    return url.replace("http://", "").replace("https://", "")


def _es_https(url: str) -> bool:
    return url.startswith("https://")


def get_client(endpoint: str | None = None) -> Minio:
    # region explícita = la de garage.toml (evita lookup de ubicación)
    url = endpoint or settings.s3_endpoint
    return Minio(
        _endpoint_sin_esquema(url),
        access_key=settings.s3_access_key,
        secret_key=settings.s3_secret_key,
        secure=_es_https(url),
        region="garage",
    )


def ensure_buckets(timeout_s: float = 15.0) -> None:
    """Crea el bucket si falta (idempotente). Falla rápido si no hay S3:
    el cliente reintenta con backoff y colgaría el arranque/requests.
    Hilo daemon abandonado en timeout (no se hace join bloqueante)."""
    import threading

    estado: dict = {}

    def _run() -> None:
        try:
            client = get_client()
            for bucket in BUCKETS:
                if not client.bucket_exists(bucket):
                    client.make_bucket(bucket)
            estado["ok"] = True
        except Exception as e:  # noqa: BLE001 - se propaga al llamador
            estado["err"] = e

    hilo = threading.Thread(target=_run, daemon=True)
    hilo.start()
    hilo.join(timeout_s)
    if hilo.is_alive():
        raise TimeoutError(f"S3 sin respuesta en {timeout_s}s")
    if "err" in estado:
        raise estado["err"]


def validar_archivo(tipo: str, filename: str, content_type: str, size: int | None = None) -> str:
    """Valida y retorna el prefijo. Lanza ValueError si no cumple."""
    regla = REGLAS.get(tipo)
    if not regla:
        raise ValueError("tipo debe ser 'modelo' o 'imagen'")
    nombre = (filename or "").lower()
    if not nombre.endswith(regla["extensiones"]):
        raise ValueError(f"extensión inválida para {tipo}: {regla['extensiones']}")
    if content_type and content_type not in regla["content_types"]:
        raise ValueError(f"content_type inválido para {tipo}")
    if size is not None and size > regla["max_bytes"]:
        raise ValueError(f"archivo excede {regla['max_bytes'] // (1024 * 1024)}MB")
    return regla["prefijo"]


def object_name(tipo: str, filename: str) -> str:
    import re
    from datetime import datetime, timezone

    base = re.sub(r"[^a-zA-Z0-9._-]", "_", (filename or "archivo").lower())
    stamp = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    return f"{REGLAS[tipo]['prefijo']}{stamp}_{base}"


def public_url(bucket: str, object_path: str) -> str:
    """Path RELATIVO estable (no expira, no ata host): el cliente lo resuelve
    contra su propia base de API. Dev y prod idénticos."""
    return f"/api/storage/{bucket}/{object_path}"


def presigned_put(bucket: str, object_path: str, expires_min: int = 15) -> str:
    from datetime import timedelta

    # Se firma contra el endpoint PÚBLICO: el PUT lo hace el navegador,
    # que no resuelve el hostname interno (garage:3900).
    return (
        get_client(settings.s3_public_endpoint)
        .presigned_put_object(bucket, object_path, expires=timedelta(minutes=expires_min))
    )


def presigned_get(bucket: str, object_path: str, expires_min: int = 10) -> str:
    from datetime import timedelta

    # Cliente contra el endpoint PÚBLICO: la URL firmada la abre el
    # navegador/AR, que no resuelve el hostname interno.
    return (
        get_client(settings.s3_public_endpoint)
        .presigned_get_object(bucket, object_path, expires=timedelta(minutes=expires_min))
    )
