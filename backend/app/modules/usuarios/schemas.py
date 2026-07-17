"""User-related Pydantic schemas."""

from datetime import datetime
from typing import Literal, Optional
from pydantic import BaseModel, ConfigDict, EmailStr, Field

PapelUsuario = Literal["GESTOR", "CONSULTOR"]


class UsuarioBase(BaseModel):
    """Base fields shared by user schemas."""

    nome: str = Field(..., min_length=2, max_length=255)
    email: EmailStr
    papel: PapelUsuario


class UsuarioCreate(UsuarioBase):
    """Payload para o GESTOR criar um novo usuário (com senha em texto puro, hasheada no backend)."""

    senha: str = Field(..., min_length=6, max_length=72)


class UsuarioUpdate(BaseModel):
    """Payload para o GESTOR atualizar um usuário existente. Todos os campos são opcionais."""

    nome: Optional[str] = Field(default=None, min_length=2, max_length=255)
    papel: Optional[PapelUsuario] = None
    senha: Optional[str] = Field(default=None, min_length=6, max_length=72)


class UsuarioResponse(UsuarioBase):
    """ORM-style response for user retrieval. Nunca expõe `senha_hash`."""

    id: str
    criado_em: datetime
    atualizado_em: datetime
    excluido: bool = False

    model_config = ConfigDict(from_attributes=True)
