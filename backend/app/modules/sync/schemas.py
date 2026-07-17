"""Sync payloads for offline-first synchronization (Dexie.js <-> backend).

Includes validators to ensure timezone-aware datetimes (UTC), necessário
para a resolução de conflitos (last-write-wins) feita pelo ``SyncService``.
"""

from __future__ import annotations

import datetime
from typing import List, Optional
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, field_validator

from app.modules.contatos.schemas import TipoNumero


class ContatoSync(BaseModel):
    id: UUID
    nome: str
    telefone: str
    email: Optional[EmailStr] = None
    tipo_numero: TipoNumero
    atualizado_em: datetime.datetime
    excluido: bool = False

    @field_validator("atualizado_em")
    def ensure_timezone(cls, v: datetime.datetime) -> datetime.datetime:  # type: ignore[override]
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc)


class SyncPayload(BaseModel):
    contatos: List[ContatoSync]
    ultima_sincronizacao: Optional[datetime.datetime] = None

    @field_validator("ultima_sincronizacao")
    def normalize_last_sync(cls, v: Optional[datetime.datetime]) -> Optional[datetime.datetime]:
        if v is None:
            return None
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc)


class SyncResponse(BaseModel):
    sucesso: bool
    contatos_atualizados: List[UUID]
    error: Optional[List[str]] = None

    model_config = ConfigDict(from_attributes=True)
