from pydantic import BaseModel, ConfigDict


class DashboardResumen(BaseModel):
    total_espacios: int
    espacios_libres: int
    espacios_ocupados: int
    productos_activos: int

    model_config = ConfigDict(from_attributes=True)