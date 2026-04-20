from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.refresh_token import RefreshToken


class RefreshTokenRepository:
    def __init__(self, session: Session) -> None:
        self.session = session

    def get_by_hash(self, token_hash: str) -> RefreshToken | None:
        return self.session.scalar(select(RefreshToken).where(RefreshToken.token_hash == token_hash))

    def revoke_by_user(self, user_id: str) -> None:
        records = list(self.session.scalars(select(RefreshToken).where(RefreshToken.user_id == user_id)))
        for record in records:
            record.revoked = True

    def add(self, refresh_token: RefreshToken) -> RefreshToken:
        self.session.add(refresh_token)
        return refresh_token
