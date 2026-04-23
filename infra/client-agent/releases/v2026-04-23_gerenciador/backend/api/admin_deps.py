from fastapi import Header, HTTPException, status

from backend.config.settings import get_settings

settings = get_settings()


def require_admin_token(
    admin_token: str | None = Header(default=None, alias=settings.admin_token_header),
) -> None:
    if not admin_token or admin_token != settings.admin_token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Admin token invalido.",
        )

