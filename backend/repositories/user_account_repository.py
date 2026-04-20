from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.user_account import UserAccount


class UserAccountRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_id(self, user_id: str) -> UserAccount | None:
        return self.session.get(UserAccount, user_id)

    def get_by_email(self, email: str) -> UserAccount | None:
        return self.session.scalar(select(UserAccount).where(UserAccount.email == email.lower()))

    def list_all(self) -> list[UserAccount]:
        return list(self.session.scalars(select(UserAccount).order_by(UserAccount.nome.asc())))

    def list_by_empresa(self, empresa_id: str) -> list[UserAccount]:
        return list(
            self.session.scalars(
                select(UserAccount).where(UserAccount.empresa_id == empresa_id).order_by(UserAccount.nome.asc())
            )
        )

    def add(self, user: UserAccount) -> UserAccount:
        self.session.add(user)
        return user
