"""User-related Pydantic schemas."""

from typing import Literal
from pydantic import BaseModel, EmailStr, SecretStr, ConfigDict


class UsuarioBase(BaseModel):
    """Base fields shared by user schemas."""

    email: EmailStr
    nome: str
    papel: Literal["GESTOR", "CONSULTOR"]


class UsuarioCreate(UsuarioBase):
    """Payload when creating a new user (includes password)."""

    senha: SecretStr


class UsuarioResponse(UsuarioBase):
    """ORM-style response for user retrieval."""

    id: int

    model_config = ConfigDict(from_attributes=True)