"""Módulo de sincronização offline-first: schemas, service e router.

Consolida o conteúdo de:
  - modules/sync/schemas.py
  - modules/sync/service.py
  - modules/sync/router.py

A regra de conflito é "last-write-wins": uma atualização vinda do cliente
offline só é aplicada se seu timestamp (``atualizado_em``) for mais recente
do que o timestamp já persistido no servidor.
"""

# ---------------------------------------------------------------------------
# Schemas
# ---------------------------------------------------------------------------

from __future__ import annotations

import datetime
from typing import List, Optional
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, EmailStr, field_validator
from sqlalchemy.ext.asyncio import AsyncSession

from app.core import get_db
from app.modules.contatos import ContatoRepository, TipoNumero


class ContatoSync(BaseModel):
    id: UUID
    nome: str
    telefone: str
    email: Optional[EmailStr] = None
    tipo_numero: TipoNumero
    atualizado_em: datetime.datetime
    excluido: bool = False

    @field_validator('atualizado_em')
    def ensure_timezone(cls, v: datetime.datetime) -> datetime.datetime:  # type: ignore[override]
        if v.tzinfo is None:
            return v.replace(tzinfo=datetime.timezone.utc)
        return v.astimezone(datetime.timezone.utc)


class SyncPayload(BaseModel):
    contatos: List[ContatoSync]
    ultima_sincronizacao: Optional[datetime.datetime] = None

    @field_validator('ultima_sincronizacao')
    def normalize_last_sync(
        cls, v: Optional[datetime.datetime]
    ) -> Optional[datetime.datetime]:
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


# ---------------------------------------------------------------------------
# Service
# ---------------------------------------------------------------------------


class SyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.contatos = ContatoRepository(db)

    @staticmethod
    def _timestamp_cliente_naive_utc(
        contato_sync: ContatoSync,
    ) -> datetime.datetime:
        try:
            return contato_sync.atualizado_em.astimezone(
                datetime.timezone.utc
            ).replace(tzinfo=None)
        except Exception:
            return datetime.datetime.now(datetime.timezone.utc).replace(
                tzinfo=None
            )

    async def sincronizar(
        self, payload: SyncPayload, usuario_nome: str
    ) -> SyncResponse:
        """Sincroniza em lote os contatos alterados offline, aplicando last-write-wins."""
        ids_confirmados: List = []

        for contato_sync in payload.contatos:
            cliente_atualizado_em = self._timestamp_cliente_naive_utc(
                contato_sync
            )
            contato_db = await self.contatos.buscar_por_id(
                str(contato_sync.id)
            )

            if contato_db:
                # CONFLITO: só aceita a versão offline se ela for mais nova que a do banco.
                if cliente_atualizado_em > contato_db.atualizado_em:
                    self.contatos.atualizar_do_offline(
                        contato_db,
                        nome=contato_sync.nome,
                        telefone=contato_sync.telefone,
                        email=contato_sync.email,
                        tipo_numero=contato_sync.tipo_numero,
                        excluido=contato_sync.excluido,
                        timestamp=cliente_atualizado_em,
                        usuario_nome=usuario_nome,
                    )
            else:
                # Registro novo, criado inteiramente offline no cliente.
                self.contatos.criar_do_offline(
                    id=str(contato_sync.id),
                    nome=contato_sync.nome,
                    telefone=contato_sync.telefone,
                    email=contato_sync.email,
                    tipo_numero=contato_sync.tipo_numero,
                    excluido=contato_sync.excluido,
                    timestamp=cliente_atualizado_em,
                    usuario_nome=usuario_nome,
                )

            ids_confirmados.append(contato_sync.id)

        await self.db.commit()
        return SyncResponse(sucesso=True, contatos_atualizados=ids_confirmados)


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------


def _build_router() -> APIRouter:
    from app.modules.auth import require_consultor

    router = APIRouter(tags=['Sincronização'])

    @router.post('', response_model=SyncResponse)
    async def sync_contatos(
        payload: SyncPayload,
        usuario=Depends(require_consultor),
        db: AsyncSession = Depends(get_db),
    ):
        """Sincronização bidirecional/offline dos contatos (Dexie.js -> backend)."""
        service = SyncService(db)
        return await service.sincronizar(payload, usuario.email)

    return router   


router = _build_router()
