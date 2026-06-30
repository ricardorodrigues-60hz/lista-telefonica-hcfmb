from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from datetime import datetime, timezone
from typing import List, Optional

from app.modules.contatos.models import Contato
from app.core.audit.models import AuditTrail
from app.modules.contatos.schemas import ContatoCreate, ContatoSync


class ContatoRepository:
    """
    Repository class for managing Contato entities in the database.
    """
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def listar_ativos(self) -> List[Contato]:
        """
        List all active contacts (not soft-deleted).

        Returns:
            List[Contato]: A list of active Contato instances.
        """
        result = await self.db.execute(select(Contato).where(Contato.excluido == False))
        return result.scalars().all()
    
    async def buscar_por_id(self, contato_id: str) -> Optional[Contato]:
        """
        Fetch a contact by its ID (UUID em formato String).

        Args:
            contato_id (str): The ID of the contact to fetch.

        Returns:
            Optional[Contato]: The Contato instance if found, else None.
        """
        result = await self.db.execute(select(Contato).where(Contato.id == contato_id))
        return result.scalars().first()
    
    async def salvar_ou_atualizar(self, contato_in: ContatoCreate, usuario_nome: str) -> Contato:
        """
        Save a new contact or update an existing one.
        Resolves ambiguity: If the contact exists, updates it; otherwise, creates a new one.

        Args:
            contato_in (ContatoCreate): The contact data to save or update.
            usuario_nome (str): The name of the user performing the operation.

        Returns:
            Contato: The saved or updated Contato instance.
        """
        contato = await self.buscar_por_id(str(contato_in.id)) if contato_in.id else None
        acao = "EDITAR" if contato else "CRIAR"
        
        # Padronizando para UTC Naive (sem tzinfo) para evitar erros de comparação com o SQLite/PostgreSQL
        now = datetime.now(timezone.utc).replace(tzinfo=None)

        if contato: 
            contato.nome = contato_in.nome
            contato.telefone = contato_in.telefone
            contato.email = contato_in.email
            contato.tipo_numero = contato_in.tipo_numero
            contato.atualizado_em = now
            contato.excluido = False  # Corrigido de 'excluido_em' para 'excluido'. Reverte soft-delete se re-editado.
        else:
            contato = Contato(
                id=str(contato_in.id),  # Garante que se o ID já vier definido (ex: UUID do front), ele seja respeitado
                nome=contato_in.nome,
                telefone=contato_in.telefone,
                email=contato_in.email,
                tipo_numero=contato_in.tipo_numero,
                criado_em=now,
                atualizado_em=now,
                excluido=False
            )
            self.db.add(contato)
        
        audit = AuditTrail(
            usuario_nome=usuario_nome,
            acao=acao,
            contato_id=contato.id,
            detalhes=f"Contato {contato.nome} ({contato.telefone}) {acao.lower()}do via painel online."
        )
        self.db.add(audit)
        await self.db.commit()
        await self.db.refresh(contato)
        return contato
            
    async def deletar_soft(self, contato_id: str, usuario_nome: str) -> bool:
        """
        Soft delete a contact by marking it as excluded.

        Args:
            contato_id (str): The ID of the contact to soft delete.
            usuario_nome (str): The name of the user performing the deletion.

        Returns:
            bool: True if the contact was successfully soft deleted, False otherwise.
        """
        contato = await self.buscar_por_id(contato_id)
        if not contato:
            return False
            
        contato.excluido = True
        contato.atualizado_em = datetime.now(timezone.utc).replace(tzinfo=None)

        audit = AuditTrail(
            usuario_nome=usuario_nome,
            acao="DELETAR",
            contato_id=contato.id,
            detalhes=f"Contato {contato.nome} marcado como excluído.",
        )
        self.db.add(audit)

        await self.db.commit()
        return True
    
    async def sincronizar_lote_offline(self, contatos_sync: List[ContatoSync], usuario_nome: str) -> List[str]:
        """
        Synchronize a batch of contacts from offline data (Dexie.js).

        Args:
            contatos_sync (List[ContatoSyncPayload]): A list of contact payloads to synchronize.
            usuario_nome (str): The name of the user performing the synchronization.

        Returns:
            List[str]: A list of IDs of the synchronized contacts.
        """
        ids_confirmados = []

        for c in contatos_sync:
            # Tratamento seguro do datetime timezone-aware vindo do schema Pydantic
            try:
                cliente_updated_at = c.atualizado_em.astimezone(timezone.utc).replace(tzinfo=None)
            except Exception:
                cliente_updated_at = datetime.now(timezone.utc).replace(tzinfo=None)

            contato_db = await self.buscar_por_id(str(c.id)) if c.id else None
            
            if contato_db:
                # CONFLITO: Só aceita se a alteração do cliente offline for mais nova do que a do banco.
                if cliente_updated_at > contato_db.atualizado_em:
                    contato_db.nome = c.nome
                    contato_db.telefone = c.telefone
                    contato_db.email = c.email
                    contato_db.tipo_numero = c.tipo_numero
                    contato_db.excluido = c.excluido  # Adicionado: Sincroniza o status de exclusão vindo do offline!
                    contato_db.atualizado_em = cliente_updated_at
                    
                    acao = "EXCLUIR" if c.excluido else "EDITAR"
                    self.db.add(AuditTrail(
                        usuario_nome=usuario_nome,
                        acao=acao + "_SYNC",
                        contato_id=str(c.id),
                        detalhes=f"Sincronização offline: Contato {c.nome} atualizado (ação: {acao.lower()})."
                    ))
            else:
                # REGISTRO NOVO: Criado inteiramente offline no cliente
                novo_contato = Contato(
                    id=str(c.id),  # Preserva o ID gerado pelo cliente para manter a consistência com o IndexedDB/Dexie
                    nome=c.nome,
                    telefone=c.telefone,
                    email=c.email,
                    tipo_numero=c.tipo_numero,
                    excluido=c.excluido,  # Adicionado para evitar que registros criados e deletados offline quebrem
                    criado_em=cliente_updated_at,
                    atualizado_em=cliente_updated_at,
                )
                self.db.add(novo_contato)
                self.db.add(AuditTrail(
                    usuario_nome=usuario_nome,
                    acao="CRIAR_SYNC",
                    contato_id=str(c.id),
                    detalhes=f"Sincronização offline: Contato {c.nome} criado."
                ))
            
            ids_confirmados.append(str(c.id))

        await self.db.commit()
        return ids_confirmados
