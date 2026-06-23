"""User-related Pydantic schemas."""

from typing import Literal
from pydantic import BaseModel, ConfigDict

class UsuarioBase(BaseModel):
    """Base fields shared by user schemas."""

    usuario_id_externo: str
    papel: Literal["GESTOR", "CONSULTOR"]

class UsuarioCreate(UsuarioBase):
    """Payload when setting a role for an external user."""
    pass

class UsuarioResponse(UsuarioBase):
    """ORM-style response for user permission retrieval."""
    
    model_config = ConfigDict(from_attributes=True)