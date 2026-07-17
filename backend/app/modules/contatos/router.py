from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.modules.usuarios.models import Usuario
from app.modules.auth.service import require_gestor, require_consultor
from app.modules.contatos.schemas import ContatoBase, ContatoResponse
from app.modules.contatos.repository import ContatoRepository


router = APIRouter(tags=["Contatos"])


@router.get("/", response_model=List[ContatoResponse])
async def get_contatos(
    usuario: Usuario = Depends(require_consultor),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os contatos ativos. Requer qualquer usuário autenticado (GESTOR ou CONSULTOR)."""
    repo = ContatoRepository(db)
    return await repo.listar_ativos()


@router.put("/{contato_id}", response_model=ContatoResponse)
async def criar_ou_atualizar_contato(
    contato_id: UUID,
    payload: ContatoBase,
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Cria ou atualiza (upsert) o contato identificado por `contato_id`. Restrito a GESTOR.

    O UUID é sempre gerado pelo cliente (offline-first); por isso o mesmo
    verbo/endpoint serve tanto para criar quanto para editar, dependendo de
    o ID já existir ou não no servidor.
    """
    repo = ContatoRepository(db)
    return await repo.salvar_ou_atualizar(contato_id, payload, usuario.email)


@router.delete("/{contato_id}", status_code=status.HTTP_204_NO_CONTENT)
async def deletar_contato(
    contato_id: UUID,
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Exclusão lógica (soft delete) de um contato. Restrito a GESTOR."""
    repo = ContatoRepository(db)
    sucesso = await repo.deletar_soft(str(contato_id), usuario.email)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Contato não encontrado.")
    return None
