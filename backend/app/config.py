from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "SmartLuben API"
    debug: bool = False
    database_url: str
    cors_origins: list[str] = ["*"]
    deepseek_api_key: str | None = None
    deepseek_base_url: str = "https://api.deepseek.com"
    deepseek_model: str = "deepseek-chat"
    ml_api_base_url: str = "http://localhost:8000"
    # S3 compatible (Garage). Sin auth dedicada en MVP.
    s3_endpoint: str = "http://garage:3900"
    s3_access_key: str = "GKcambio"
    s3_secret_key: str = "cambio"
    # Endpoint S3 alcanzable desde navegador/AR (firma de presigned GET).
    # Dev: http://localhost:3900 (o IP LAN si incluye móvil) | Prod: https://tu-dominio/s3
    s3_public_endpoint: str = "http://localhost:3900"

    model_config = SettingsConfigDict(
        case_sensitive=False,
        extra="ignore",
    )


settings = Settings()
