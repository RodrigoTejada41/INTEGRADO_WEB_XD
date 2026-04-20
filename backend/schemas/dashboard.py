from pydantic import BaseModel


class DashboardSummaryResponse(BaseModel):
    empresas: int
    usuarios: int
    ativos: int
