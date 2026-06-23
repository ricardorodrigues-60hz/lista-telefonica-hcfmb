from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.database import get_db
from app.models import Usuario
from app.core.auth import get_current_user, require_gestor
from app.schemas import ContatoResponse, ContatoCreate, SyncPayload, SyncResponse, IdPayload
from app.repositories import ContatoRepository


router = APIRouter(tags=["Contatos"])


@router.get("/", response_model=List[ContatoResponse])
async def get_contatos(db: AsyncSession = Depends(get_db)):
    """
    Endpoint para listar todos os contatos ativos.

    Args:
        db (AsyncSession): Sessão assíncrona do banco de dados, injetada via Depends.

    Returns:
        List[ContatoResponse]: Uma lista de contatos ativos.
    """
    repo = ContatoRepository(db)
    return await repo.listar_ativos()

@router.post("/criar-editar", response_model=ContatoResponse)
async def criar_editar_contato(
    contato_in: ContatoCreate,
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para criar ou editar um contato.
    Se o contato já existir (identificado por ID), ele será atualizado;
    caso contrário, um novo contato será criado.

    Args:
        contato_in (ContatoCreate): Dados do contato a ser criado ou editado.
        usuario (Usuario): O usuário autenticado, injetado via Depends(require_gestor) para garantir que apenas gestores possam acessar este endpoint.
        db
        (AsyncSession): Sessão assíncrona do banco de dados, injetada via Depends.
    Returns:
        ContatoResponse: O contato criado ou atualizado.
    """
    repo = ContatoRepository(db)
    return await repo.salvar_ou_atualizar(contato_in, usuario.usuario_id_externo)
    
@router.post("/deletar")
async def deletar_contato(
    payload: IdPayload,
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db)
):
    """
    Endpoint para realizar exclusão lógica (soft delete) de um contato. O contato não é removido do banco, mas sim marcado como inativo.
    Args:
        payload (dict): Um dicionário contendo o ID do contato a ser deletado, no formato {"id": <contato_id>}.
        usuario (Usuario): O usuário autenticado, injetado via Depends(require_gestor) para garantir que apenas gestores possam acessar este endpoint.
        db (AsyncSession): Sessão assíncrona do banco de dados, injetada via Depends.
    Returns:
        dict: Uma mensagem indicando o sucesso da operação.
    """
    contato_id = payload.id
    if not contato_id:
        raise HTTPException(status_code=400, detail="ID do contato é obrigatório.")

    repo = ContatoRepository(db)
    contato = await repo.deletar_soft(str(contato_id), usuario.usuario_id_externo)
    if not contato:
        raise HTTPException(status_code=404, detail="Contato não encontrado.")
    
    return {"message": "Contato marcado como excluído com sucesso."}

@router.post("/sync", response_model=SyncResponse)
async def sync_contatos(
    payload: SyncPayload,
    usuario: Usuario = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Endpoint inteligente de sincronização bidirecional/offline
    repo = ContatoRepository(db)
    # chama o método existente do repositório para sincronização em lote
    ids_confirmados = await repo.sincronizar_lote_offline(payload.contatos, usuario.usuario_id_externo)
    return SyncResponse(sucesso=True, contatos_atualizados=ids_confirmados)
