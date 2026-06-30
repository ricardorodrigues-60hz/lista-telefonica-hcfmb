from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.modules.usuarios.schemas import UsuarioResponse
from app.modules.usuarios.repository import UsuarioRepository
from app.core.auth import get_current_user

router = APIRouter(tags=["Permissões de Usuários"])

@router.get("/", response_model=List[UsuarioResponse])
async def listar_permissoes(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = UsuarioRepository(db)
    if getattr(current_user, "papel", None) != "GESTOR":
        return [UsuarioResponse.model_validate(current_user)]
    users = await repo.listar()
    return [UsuarioResponse.model_validate(u) for u in users]

@router.get("/{usuario_id_externo}", response_model=UsuarioResponse)
async def get_permissao(usuario_id_externo: str, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = UsuarioRepository(db)
    usuario = await repo.buscar_por_id_externo(usuario_id_externo)
    if not usuario:
        raise HTTPException(status_code=404, detail="Permissão não encontrada")
    if getattr(current_user, "papel", None) != "GESTOR" and current_user.usuario_id_externo != usuario.usuario_id_externo:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return UsuarioResponse.model_validate(usuario)
