"""Authentication-related Pydantic schemas.

These models are intentionally minimal and avoid exposing secrets.
"""

from typing import Literal
from pydantic import BaseModel, EmailStr, Field


class LoginRequest(BaseModel):
    """Credenciais de login: e-mail funcional + senha."""

    login: EmailStr = Field(..., description="E-mail funcional do usuário")
    senha: str = Field(..., min_length=1)


class TokenResponse(BaseModel):
    """Par de tokens JWT retornado por /auth/login e /auth/refresh."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    papel: Literal["GESTOR", "CONSULTOR"]
    nome: str


class RefreshRequest(BaseModel):
    refresh_token: str


class LogoutRequest(BaseModel):
    refresh_token: str
