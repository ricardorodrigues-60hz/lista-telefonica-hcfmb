from typing import List
from uuid import uuid4

from app.core.auth import UsuarioAutenticado, get_current_user, require_gestor
from app.core.database import get_db
from app.modules.contatos.repository import ContatoRepository
from app.modules.contatos.schemas import (
    ContatoCreate,
    ContatoUpdate,
    ContatoResponse,
    SyncPayload,
    SyncResponse,
)
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

router = APIRouter(tags=["Contatos"])


# List contacts
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


# Create contact (POST /)
@router.post("/", response_model=ContatoResponse, status_code=status.HTTP_201_CREATED)
async def create_contato(
    contato_in: ContatoCreate,
    usuario: UsuarioAutenticado = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """
    Create a new contact via RESTful POST.
    
    O ID pode ser fornecido como UUID string ou deixado vazio.
    Se omitido, o servidor gera um UUID automaticamente.
    """
    repo = ContatoRepository(db)
    
    # Se ID não foi fornecido, gera um novo UUID
    if not contato_in.id:
        contato_in.id = str(uuid4())
    
    return await repo.criar_contato(contato_in, usuario.usuario_id_externo)


# Update contact
@router.put("/{contato_id}", response_model=ContatoResponse)
async def update_contato(
    contato_id: str,
    contato_in: ContatoUpdate,
    usuario: UsuarioAutenticado = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Update an existing contact identified by ID."""
    repo = ContatoRepository(db)
    contato = await repo.atualizar_contato(contato_id, contato_in, usuario.usuario_id_externo)
    if not contato:
        raise HTTPException(status_code=404, detail="Contato não encontrado.")
    return contato


# Soft delete contact (DELETE /{contato_id})
@router.delete("/{contato_id}")
async def delete_contato(
    contato_id: str,
    usuario: UsuarioAutenticado = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Soft‑delete a contact identified by ID via DELETE request."""
    repo = ContatoRepository(db)
    sucesso = await repo.deletar_soft(contato_id, usuario.usuario_id_externo)
    if not sucesso:
        raise HTTPException(status_code=404, detail="Contato não encontrado.")
    return {"message": "Contato marcado como excluído com sucesso."}

# Sync contacts
@router.post("/sync", response_model=SyncResponse)
async def sync_contatos(
    payload: SyncPayload,
    usuario: UsuarioAutenticado = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Endpoint inteligente de sincronização bidirecional/offline
    repo = ContatoRepository(db)
    # chama o método existente do repositório para sincronização em lote
    usuario_id_externo = getattr(usuario, "usuario_id_externo", None) or getattr(
        usuario, "nome", None
    )
    ids_confirmados = await repo.sincronizar_lote_offline(
        payload.contatos, usuario_id_externo
    )
    return SyncResponse(sucesso=True, contatos_atualizados=ids_confirmados)
