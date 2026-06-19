"""Schemas package exports for the application.

Use relative imports so the package can be imported as `app.schemas`.
"""

from .auth import LoginRequest, Token, TokenData, TokenResponse, RefreshRequest
from .usuarios import UsuarioCreate, UsuarioResponse
from .contatos import (
	ContatoCreate,
	ContatoResponse,
	ContatoSync,
	SyncPayload,
	SyncResponse,
	IdPayload,
	ContatoUpdate,
)

__all__ = [
	"LoginRequest",
	"Token",
	"TokenData",
    "TokenResponse",
    "RefreshRequest",
	"UsuarioCreate",
	"UsuarioResponse",
	"ContatoCreate",
	"ContatoResponse",
	"ContatoSync",
	"SyncPayload",
	"SyncResponse",
	"IdPayload",
	"ContatoUpdate",
]