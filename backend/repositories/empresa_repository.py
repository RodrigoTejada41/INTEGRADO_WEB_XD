from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.empresa import Empresa


class EmpresaRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def list_all(self) -> list[Empresa]:
        return list(self.session.scalars(select(Empresa).order_by(Empresa.nome.asc())))

    def get_by_id(self, empresa_id: str) -> Empresa | None:
        return self.session.get(Empresa, empresa_id)

    def get_by_cnpj(self, cnpj: str) -> Empresa | None:
        return self.session.scalar(select(Empresa).where(Empresa.cnpj == cnpj))

    def add(self, empresa: Empresa) -> Empresa:
        self.session.add(empresa)
        return empresa
