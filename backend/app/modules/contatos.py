"""Módulo de contatos e auditoria: modelos, schemas, repositories e router.

Consolida o conteúdo de:
  - modules/auditoria/models.py    (AuditTrail)
  - modules/auditoria/repository.py (AuditoriaRepository)
  - modules/contatos/models.py
  - modules/contatos/schemas.py
  - modules/contatos/repository.py
  - modules/contatos/router.py
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------------

import json
from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core import Base


class AuditTrail(Base):
    """Trilha de auditoria imutável para qualquer operação de escrita no sistema."""

    __tablename__ = "audit_trail"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    usuario_nome: Mapped[str] = mapped_column(String, nullable=False)
    acao: Mapped[str] = mapped_column(String, nullable=False)  # "CRIAR", "EDITAR", "EXCLUIR"...
    tabela: Mapped[str] = mapped_column(String, nullable=False, default="contatos")
    registro_id: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    detalhes: Mapped[str] = mapped_column(String, nullable=False)
    dados_modificados: Mapped[Optional[str]] = mapped_column(String, nullable=True)  # JSON serializado

    # Gravado nativamente pelo banco de dados no momento do INSERT
    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
    )


class Contato(Base):
    __tablename__ = "contatos"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, index=True)  # UUID
    nome: Mapped[str] = mapped_column(String, nullable=False, index=True)
    telefone: Mapped[str] = mapped_column(String(50), nullable=False)
    email: Mapped[Optional[str]] = mapped_column(String, nullable=True)
    tipo_numero: Mapped[str] = mapped_column(String, nullable=False)  # "institucional" ou "publico"

    criado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now()
    )
    atualizado_em: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now()
    )
    excluido: Mapped[bool] = mapped_column(Boolean, default=False)


import datetime
import re
from enum import Enum
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    field_validator,
)


class TipoNumero(str, Enum):
    INSTITUCIONAL = "institucional"
    PUBLICO = "publico"


class ContatoBase(BaseModel):
    nome: str
    telefone: str
    email: Optional[EmailStr] = None
    tipo_numero: TipoNumero = TipoNumero.PUBLICO

    @field_validator("telefone")
    def validate_telefone(cls, v: str) -> str:  # type: ignore[override]
        if not re.match(r"^[0-9\+\(\)\s\-\.]+$", v):
            raise ValueError("telefone inválido")
        digits = re.sub(r"\D", "", v)
        if len(digits) < 8:
            raise ValueError("telefone inválido")
        return v


class ContatoUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    tipo_numero: Optional[TipoNumero] = None


class ContatoResponse(ContatoBase):
    id: UUID
    criado_em: Optional[datetime.datetime] = None
    atualizado_em: datetime.datetime
    excluido: bool = False

    model_config = ConfigDict(from_attributes=True)


# ---------------------------------------------------------------------------
# Repositories
# ---------------------------------------------------------------------------

from datetime import timezone
from typing import List

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select


def _serializar(dados: dict) -> str:
    return json.dumps(dados, default=str, ensure_ascii=False)


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class AuditoriaRepository:
    """Repository responsável por registrar e consultar a trilha de auditoria.

    ``registrar`` apenas prepara (``add``) o registro na sessão corrente e não
    executa commit: cabe ao chamador commitar a transação, garantindo que a
    mudança de dado e sua auditoria sejam atômicas.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    def registrar(
        self,
        *,
        usuario_nome: str,
        acao: str,
        tabela: str,
        registro_id: Optional[str],
        detalhes: str,
        dados_modificados: Optional[dict] = None,
    ) -> AuditTrail:
        entrada = AuditTrail(
            usuario_nome=usuario_nome,
            acao=acao,
            tabela=tabela,
            registro_id=registro_id,
            detalhes=detalhes,
            dados_modificados=_serializar(dados_modificados) if dados_modificados is not None else None,
        )
        self.db.add(entrada)
        return entrada

    async def listar_por_tabela(self, tabela: str) -> List[AuditTrail]:
        result = await self.db.execute(
            select(AuditTrail).where(AuditTrail.tabela == tabela).order_by(AuditTrail.criado_em.desc())
        )
        return list(result.scalars().all())


class ContatoRepository:
    """Repository responsável pelo CRUD e persistência de Contato.

    A resolução de conflitos da sincronização offline fica no
    ``SyncService`` (módulo ``sync``); este repository apenas expõe métodos
    de persistência puros que aceitam um timestamp explícito.
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

    async def criar(
        self, contato_id: UUID, contato_in: ContatoBase, usuario_nome: str
    ) -> Contato:
        """Cria um novo contato com o `contato_id` fornecido (fluxo online).

        O UUID já é gerado pelo cliente (offline-first). Lança ``ValueError``
        se já existir um contato com esse ID.
        """
        existente = await self.buscar_por_id(str(contato_id))
        if existente:
            raise ValueError("Já existe um contato com esse ID.")

        now = _now_naive_utc()
        contato = Contato(
            id=str(contato_id),
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
            acao="CRIAR",
            tabela="contatos",
            registro_id=contato.id,
            detalhes=f"Contato {contato.nome} ({contato.telefone}) criado via painel online.",
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

    async def atualizar(
        self, contato_id: UUID, contato_in: ContatoBase, usuario_nome: str
    ) -> Optional[Contato]:
        """Atualiza o contato existente identificado por `contato_id` (fluxo online)."""
        contato = await self.buscar_por_id(str(contato_id))
        if not contato:
            return None

        contato.nome = contato_in.nome
        contato.telefone = contato_in.telefone
        contato.email = contato_in.email
        contato.tipo_numero = contato_in.tipo_numero
        contato.atualizado_em = _now_naive_utc()
        contato.excluido = False  # Reverte soft-delete se o contato for re-editado.

        self.auditoria.registrar(
            usuario_nome=usuario_nome,
            acao="EDITAR",
            tabela="contatos",
            registro_id=contato.id,
            detalhes=f"Contato {contato.nome} ({contato.telefone}) editado via painel online.",
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

        Não comita a transação: o chamador (``SyncService``) decide quando comitar o lote.
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

        Não comita a transação: o chamador (``SyncService``) decide quando comitar o lote.
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


# ---------------------------------------------------------------------------
# Router
# ---------------------------------------------------------------------------

from fastapi import APIRouter, Depends, HTTPException, status

from app.core import get_db

router = APIRouter(tags=["Contatos"])


def _build_router() -> APIRouter:
    from app.modules.auth import require_gestor, require_consultor

    r = APIRouter(tags=["Contatos"])

    @r.get("/", response_model=List[ContatoResponse])
    async def get_contatos(
        usuario=Depends(require_consultor),
        db: AsyncSession = Depends(get_db),
    ):
        """Lista todos os contatos ativos. Requer qualquer usuário autenticado (GESTOR ou CONSULTOR)."""
        repo = ContatoRepository(db)
        return await repo.listar_ativos()

    @r.post("/{contato_id}", response_model=ContatoResponse, status_code=status.HTTP_201_CREATED)
    async def create_contato(
        contato_id: UUID,
        payload: ContatoBase,
        usuario=Depends(require_gestor),
        db: AsyncSession = Depends(get_db),
    ):
        """Cria um novo contato com o `contato_id` fornecido. Restrito a GESTOR.

        O UUID é sempre gerado pelo cliente (offline-first).
        """
        repo = ContatoRepository(db)
        try:
            return await repo.criar(contato_id, payload, usuario.email)
        except ValueError as exc:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(exc))

    @r.put("/{contato_id}", response_model=ContatoResponse)
    async def update_contato(
        contato_id: UUID,
        payload: ContatoBase,
        usuario=Depends(require_gestor),
        db: AsyncSession = Depends(get_db),
    ):
        """Atualiza o contato identificado por `contato_id`. Restrito a GESTOR."""
        repo = ContatoRepository(db)
        contato = await repo.atualizar(contato_id, payload, usuario.email)
        if not contato:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contato não encontrado.")
        return contato

    @r.delete("/{contato_id}", status_code=status.HTTP_204_NO_CONTENT)
    async def deletar_contato(
        contato_id: UUID,
        usuario=Depends(require_gestor),
        db: AsyncSession = Depends(get_db),
    ):
        """Exclusão lógica (soft delete) de um contato. Restrito a GESTOR."""
        repo = ContatoRepository(db)
        sucesso = await repo.deletar_soft(str(contato_id), usuario.email)
        if not sucesso:
            raise HTTPException(status_code=404, detail="Contato não encontrado.")
        return None

    return r


router = _build_router()
