"""Sincronização offline-first (Dexie.js <-> backend) e resolução de conflitos.

A regra de conflito é "last-write-wins": uma atualização vinda do cliente
offline só é aplicada se seu timestamp (``atualizado_em``) for mais recente
do que o timestamp já persistido no servidor. A persistência em si delega
para ``ContatoRepository`` (módulo ``contatos``); aqui vive apenas a decisão
de negócio.
"""

from datetime import datetime, timezone
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.contatos.repository import ContatoRepository
from app.modules.sync.schemas import ContatoSync, SyncPayload, SyncResponse


class SyncService:
    def __init__(self, db: AsyncSession):
        self.db = db
        self.contatos = ContatoRepository(db)

    @staticmethod
    def _timestamp_cliente_naive_utc(contato_sync: ContatoSync) -> datetime:
        try:
            return contato_sync.atualizado_em.astimezone(timezone.utc).replace(tzinfo=None)
        except Exception:
            return datetime.now(timezone.utc).replace(tzinfo=None)

    async def sincronizar(self, payload: SyncPayload, usuario_nome: str) -> SyncResponse:
        """Sincroniza em lote os contatos alterados offline, aplicando last-write-wins."""
        ids_confirmados: List = []

        for contato_sync in payload.contatos:
            cliente_atualizado_em = self._timestamp_cliente_naive_utc(contato_sync)
            contato_db = await self.contatos.buscar_por_id(str(contato_sync.id))

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
