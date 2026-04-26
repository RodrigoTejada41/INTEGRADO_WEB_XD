from __future__ import annotations

from fastapi import Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.models.user import User

ROLE_PERMISSIONS: dict[str, set[str]] = {
    'admin': {
        'dashboard.view',
        'reports.view',
        'records.view',
        'history.view',
        'remote_clients.view',
        'remote_clients.manage',
        'settings.view',
        'settings.manage',
        'users.manage',
        'jobs.retry',
    },
    'analyst': {
        'dashboard.view',
        'reports.view',
        'records.view',
        'history.view',
        'remote_clients.view',
    },
    'viewer': {
        'dashboard.view',
        'remote_clients.view',
    },
    'client': {
        'client.dashboard.view',
        'client.reports.view',
    },
}


def require_web_user(request: Request, db: Session = Depends(get_db)) -> User:
    user_id = request.session.get('user_id')
    if not user_id:
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={'Location': '/login'})
    user = db.get(User, user_id)
    if not user:
        request.session.clear()
        raise HTTPException(status_code=status.HTTP_302_FOUND, headers={'Location': '/login'})
    return user


def require_web_role(*allowed_roles: str):
    def dependency(user: User = Depends(require_web_user)) -> User:
        if allowed_roles and user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Acesso negado para este perfil.',
            )
        return user

    return dependency


def require_web_permission(*permissions: str):
    def dependency(user: User = Depends(require_web_user)) -> User:
        granted = ROLE_PERMISSIONS.get(user.role, set())
        if permissions and not any(permission in granted for permission in permissions):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail='Acesso negado para esta operacao.',
            )
        return user

    return dependency


def require_client_user(user: User = Depends(require_web_user)) -> User:
    if user.role != 'client' or not user.empresa_id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail='Acesso restrito ao portal do cliente.',
        )
    return user
