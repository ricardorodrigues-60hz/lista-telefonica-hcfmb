"""Authentication-related Pydantic schemas.

These models are intentionally minimal and avoid exposing secrets.
"""

from typing import Optional
from pydantic import BaseModel, EmailStr, SecretStr, ConfigDict


class LoginRequest(BaseModel):
    """Request body for user login.

    Attributes:
        login: user email
        senha: password (kept as SecretStr)
    """

    login: EmailStr
    senha: SecretStr


class Token(BaseModel):
    """Access and refresh tokens returned after authentication."""

    access_token: str
    refresh_token: str
    token_type: str
    papel: str
    nome: str


class TokenData(BaseModel):
    """Decoded token data used for authentication context."""

    email: Optional[str] = None
    papel: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)


class UsuarioMeta(BaseModel):
    """Minimal user metadata returned with tokens."""

    nome: str
    login: str
    papel: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    usuario: UsuarioMeta


class RefreshRequest(BaseModel):
    refresh_token: str