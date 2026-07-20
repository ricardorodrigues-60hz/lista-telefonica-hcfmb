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


@router.post("/{contato_id}", response_model=ContatoResponse, status_code=status.HTTP_201_CREATED)
async def create_contato(
    contato_id: UUID,
    payload: ContatoBase,
    usuario: Usuario = Depends(require_gestor),
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


@router.put("/{contato_id}", response_model=ContatoResponse)
async def update_contato(
    contato_id: UUID,
    payload: ContatoBase,
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza o contato identificado por `contato_id`. Restrito a GESTOR."""
    repo = ContatoRepository(db)
    contato = await repo.atualizar(contato_id, payload, usuario.email)
    if not contato:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Contato não encontrado.")
    return contato


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
