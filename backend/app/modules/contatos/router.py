from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.modules.usuarios.models import Usuario
from app.modules.auth.service import require_gestor, require_consultor
from app.modules.contatos.schemas import ContatoResponse, ContatoCreate, IdPayload
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


@router.post("/criar-editar", response_model=ContatoResponse)
async def criar_editar_contato(
    contato_in: ContatoCreate,
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Cria ou edita um contato. Restrito a GESTOR."""
    repo = ContatoRepository(db)
    return await repo.salvar_ou_atualizar(contato_in, usuario.email)


@router.post("/deletar")
async def deletar_contato(
    payload: IdPayload,
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Exclusão lógica (soft delete) de um contato. Restrito a GESTOR."""
    contato_id = payload.id
    if not contato_id:
        raise HTTPException(status_code=400, detail="ID do contato é obrigatório.")

    repo = ContatoRepository(db)
    contato = await repo.deletar_soft(str(contato_id), usuario.email)
    if not contato:
        raise HTTPException(status_code=404, detail="Contato não encontrado.")

    return {"message": "Contato marcado como excluído com sucesso."}
