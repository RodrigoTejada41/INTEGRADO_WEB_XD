from pydantic import BaseModel, EmailStr, Field


class UserCreateRequest(BaseModel):
    empresa_id: str | None = None
    nome: str = Field(min_length=2, max_length=120)
    email: EmailStr
    password: str = Field(min_length=8, max_length=120)
    role: str = Field(default="admin", pattern="^(superadmin|admin|manager|viewer)$")


class UserUpdateRequest(BaseModel):
    nome: str | None = Field(default=None, min_length=2, max_length=120)
    role: str | None = Field(default=None, pattern="^(superadmin|admin|manager|viewer)$")
    ativo: bool | None = None


class UserResponse(BaseModel):
    id: str
    empresa_id: str
    nome: str
    email: EmailStr
    role: str
    ativo: bool
