from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class UserCreateRequest(BaseModel):
    username: str = Field(min_length=3, max_length=100)
    full_name: str = Field(min_length=1, max_length=200)
    password: str = Field(min_length=8, max_length=128)
    role: str = Field(default="viewer", min_length=3, max_length=50)
    empresa_id: str | None = Field(default=None, min_length=8, max_length=32)
    scope_type: str | None = Field(default=None, pattern="^(company|branch_set)$")
    allowed_branch_codes: list[str] = Field(default_factory=list)


class UserUpdateRequest(BaseModel):
    full_name: str = Field(min_length=1, max_length=200)
    role: str = Field(default="viewer", min_length=3, max_length=50)
    empresa_id: str | None = Field(default=None, min_length=8, max_length=32)
    scope_type: str | None = Field(default=None, pattern="^(company|branch_set)$")
    allowed_branch_codes: list[str] = Field(default_factory=list)
    is_active: bool = True
    password: str | None = Field(default=None, min_length=8, max_length=128)


class UserResponse(BaseModel):
    id: int
    username: str
    full_name: str
    role: str
    empresa_id: str | None = None
    scope_type: str | None = None
    allowed_branch_codes: list[str] = Field(default_factory=list)
    is_active: bool
    last_login_at: datetime | None = None
