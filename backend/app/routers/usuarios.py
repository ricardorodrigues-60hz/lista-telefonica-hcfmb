from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List
import asyncio

from app.database import get_db
from app.schemas import UsuarioCreate, UsuarioResponse
from app.repositories import UsuarioRepository
from app.core.auth import get_current_user, require_gestor
from app.core.passwords import async_get_password_hash
from pydantic import SecretStr


router = APIRouter(tags=["Usuários"])


@router.get("/", response_model=List[UsuarioResponse])
async def listar_usuarios(current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    # Gestores veem todos; consultores apenas o próprio registro
    repo = UsuarioRepository(db)
    if getattr(current_user, "papel", None) != "GESTOR":
        return [UsuarioResponse.from_orm(current_user)]
    users = await repo.listar()
    return [UsuarioResponse.from_orm(u) for u in users]


@router.get("/{user_id}", response_model=UsuarioResponse)
async def get_usuario(user_id: int, current_user=Depends(get_current_user), db: AsyncSession = Depends(get_db)):
    repo = UsuarioRepository(db)
    usuario = await repo.buscar_por_id(user_id)
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    if getattr(current_user, "papel", None) != "GESTOR" and current_user.id != usuario.id:
        raise HTTPException(status_code=403, detail="Acesso negado")
    return UsuarioResponse.from_orm(usuario)


@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def criar_usuario(payload: UsuarioCreate, usuario=Depends(require_gestor), db: AsyncSession = Depends(get_db)):
    repo = UsuarioRepository(db)
    senha_plain = payload.senha.get_secret_value()
    # hashing is blocking - use centralized async helper
    senha_hash = await async_get_password_hash(senha_plain)
    novo = await repo.criar(email=payload.email, nome=payload.nome, senha_hash=senha_hash, papel=payload.papel)
    return UsuarioResponse.from_orm(novo)


@router.patch("/{user_id}", response_model=UsuarioResponse)
async def atualizar_usuario(user_id: int, payload: UsuarioCreate, usuario=Depends(require_gestor), db: AsyncSession = Depends(get_db)):
    # Reuse UsuarioCreate fields for simplicity; senha será ignorada if not provided
    repo = UsuarioRepository(db)
    fields = {"email": payload.email, "nome": payload.nome, "papel": payload.papel}
    updated = await repo.atualizar(user_id, **fields)
    if not updated:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return UsuarioResponse.from_orm(updated)


@router.post("/{user_id}/senha")
async def trocar_senha(user_id: int, senha: SecretStr, usuario=Depends(require_gestor), db: AsyncSession = Depends(get_db)):
    senha_plain = senha.get_secret_value()
    senha_hash = await async_get_password_hash(senha_plain)
    repo = UsuarioRepository(db)
    ok = await repo.atualizar_senha(user_id, senha_hash)
    if not ok:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"message": "Senha atualizada com sucesso."}


@router.delete("/{user_id}")
async def deletar_usuario(user_id: int, usuario=Depends(require_gestor), db: AsyncSession = Depends(get_db)):
    repo = UsuarioRepository(db)
    ok = await repo.deletar_soft(user_id)
    if not ok:
        raise HTTPException(status_code=404, detail="Usuário não encontrado")
    return {"message": "Usuário removido."}
