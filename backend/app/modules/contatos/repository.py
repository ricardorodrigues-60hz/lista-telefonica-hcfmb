from datetime import datetime, timezone
from typing import List, Optional
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.modules.contatos.models import Contato
from app.modules.contatos.schemas import ContatoBase
from app.modules.auditoria.repository import AuditoriaRepository


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class ContatoRepository:
    """Repository responsável pelo CRUD e persistência de Contato.

    A resolução de conflitos da sincronização offline fica no
    ``SyncService`` (módulo ``sync``); este repository apenas expõe métodos
    de persistência puros que aceitam um timestamp explícito, para que tanto
    o fluxo "online" (``salvar_ou_atualizar``) quanto o fluxo de sync possam
    reutilizá-lo.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.auditoria = AuditoriaRepository(db)

    async def listar_ativos(self) -> List[Contato]:
        """Lista todos os contatos ativos (não excluídos por soft-delete)."""
        result = await self.db.execute(select(Contato).where(Contato.excluido == False))
        return list(result.scalars().all())

    async def buscar_por_id(self, contato_id: str) -> Optional[Contato]:
        result = await self.db.execute(select(Contato).where(Contato.id == contato_id))
        return result.scalars().first()

    async def salvar_ou_atualizar(
        self, contato_id: UUID, contato_in: ContatoBase, usuario_nome: str
    ) -> Contato:
        """Cria ou atualiza (upsert) o contato identificado por `contato_id` (fluxo online).

        Se o contato já existir, é atualizado; caso contrário, um novo
        contato é criado com esse mesmo ID (UUID gerado pelo cliente).
        """
        contato = await self.buscar_por_id(str(contato_id))
        acao = "EDITAR" if contato else "CRIAR"

        now = _now_naive_utc()

        if contato:
            contato.nome = contato_in.nome
            contato.telefone = contato_in.telefone
            contato.email = contato_in.email
            contato.tipo_numero = contato_in.tipo_numero
            contato.atualizado_em = now
            contato.excluido = False  # Reverte soft-delete se o contato for re-editado.
        else:
            contato = Contato(
                id=str(contato_id),  # Respeita o UUID já gerado pelo cliente
                nome=contato_in.nome,
                telefone=contato_in.telefone,
                email=contato_in.email,
                tipo_numero=contato_in.tipo_numero,
                criado_em=now,
                atualizado_em=now,
                excluido=False,
            )
            self.db.add(contato)

        self.auditoria.registrar(
            usuario_nome=usuario_nome,
            acao=acao,
            tabela="contatos",
            registro_id=contato.id,
            detalhes=f"Contato {contato.nome} ({contato.telefone}) {acao.lower()}do via painel online.",
            dados_modificados={
                "nome": contato.nome,
                "telefone": contato.telefone,
                "email": contato.email,
                "tipo_numero": contato.tipo_numero,
            },
        )

        await self.db.commit()
        await self.db.refresh(contato)
        return contato

    async def deletar_soft(self, contato_id: str, usuario_nome: str) -> bool:
        """Exclusão lógica (soft delete) de um contato."""
        contato = await self.buscar_por_id(contato_id)
        if not contato:
            return False

        contato.excluido = True
        contato.atualizado_em = _now_naive_utc()

        self.auditoria.registrar(
            usuario_nome=usuario_nome,
            acao="DELETAR",
            tabela="contatos",
            registro_id=contato.id,
            detalhes=f"Contato {contato.nome} marcado como excluído.",
            dados_modificados={"excluido": True},
        )

        await self.db.commit()
        return True

    # --- Usados exclusivamente pelo SyncService (modules.sync) -------------

    def criar_do_offline(
        self,
        *,
        id: str,
        nome: str,
        telefone: str,
        email: Optional[str],
        tipo_numero: str,
        excluido: bool,
        timestamp: datetime,
        usuario_nome: str,
    ) -> Contato:
        """Cria um contato a partir de um payload offline, preservando o timestamp do cliente.

        Não comita a transação: o chamador (``SyncService``) decide quando
        comitar o lote inteiro.
        """
        contato = Contato(
            id=id,
            nome=nome,
            telefone=telefone,
            email=email,
            tipo_numero=tipo_numero,
            excluido=excluido,
            criado_em=timestamp,
            atualizado_em=timestamp,
        )
        self.db.add(contato)

        self.auditoria.registrar(
            usuario_nome=usuario_nome,
            acao="CRIAR_SYNC",
            tabela="contatos",
            registro_id=id,
            detalhes=f"Sincronização offline: Contato {nome} criado.",
            dados_modificados={"nome": nome, "telefone": telefone, "excluido": excluido},
        )
        return contato

    def atualizar_do_offline(
        self,
        contato: Contato,
        *,
        nome: str,
        telefone: str,
        email: Optional[str],
        tipo_numero: str,
        excluido: bool,
        timestamp: datetime,
        usuario_nome: str,
    ) -> Contato:
        """Atualiza um contato existente a partir de um payload offline vencedor do conflito.

        Não comita a transação: o chamador (``SyncService``) decide quando
        comitar o lote inteiro.
        """
        contato.nome = nome
        contato.telefone = telefone
        contato.email = email
        contato.tipo_numero = tipo_numero
        contato.excluido = excluido
        contato.atualizado_em = timestamp

        acao_base = "EXCLUIR" if excluido else "EDITAR"
        self.auditoria.registrar(
            usuario_nome=usuario_nome,
            acao=f"{acao_base}_SYNC",
            tabela="contatos",
            registro_id=contato.id,
            detalhes=f"Sincronização offline: Contato {nome} atualizado (ação: {acao_base.lower()}).",
            dados_modificados={"nome": nome, "telefone": telefone, "excluido": excluido},
        )
        return contato
