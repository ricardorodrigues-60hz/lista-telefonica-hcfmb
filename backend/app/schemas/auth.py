"""Authentication-related Pydantic schemas.

These models are intentionally minimal and avoid exposing secrets.
"""

from typing import Optional
from pydantic import BaseModel, ConfigDict

class LoginRequest(BaseModel):
    usuario_id_externo: str

class Token(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    papel: str

class TokenData(BaseModel):
    usuario_id_externo: Optional[str] = None
    papel: Optional[str] = None

    model_config = ConfigDict(populate_by_name=True)

class UsuarioMeta(BaseModel):
    usuario_id_externo: str
    papel: str

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str
    usuario: UsuarioMeta

class RefreshRequest(BaseModel):
    refresh_token: str