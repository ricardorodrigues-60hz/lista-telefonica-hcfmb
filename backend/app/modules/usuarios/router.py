from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.core.database import get_db
from app.modules.usuarios.models import Usuario
from app.modules.usuarios.schemas import UsuarioCreate, UsuarioUpdate, UsuarioResponse
from app.modules.usuarios.repository import UsuarioRepository
from app.modules.auth.service import get_current_user, require_gestor

router = APIRouter(tags=["Usuários"])


@router.get("/me", response_model=UsuarioResponse)
async def obter_perfil(usuario: Usuario = Depends(get_current_user)):
    """Retorna os dados do próprio usuário autenticado."""
    return UsuarioResponse.model_validate(usuario)


@router.get("/", response_model=List[UsuarioResponse])
async def listar_usuarios(
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Lista todos os usuários ativos. Restrito a GESTOR."""
    repo = UsuarioRepository(db)
    usuarios = await repo.listar_ativos()
    return [UsuarioResponse.model_validate(u) for u in usuarios]


@router.get("/{usuario_id}", response_model=UsuarioResponse)
async def obter_usuario(
    usuario_id: str,
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Obtém um usuário por ID. Restrito a GESTOR."""
    repo = UsuarioRepository(db)
    encontrado = await repo.buscar_por_id(usuario_id)
    if not encontrado or encontrado.excluido:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")
    return UsuarioResponse.model_validate(encontrado)


@router.post("/", response_model=UsuarioResponse, status_code=status.HTTP_201_CREATED)
async def criar_usuario(
    payload: UsuarioCreate,
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Cria um novo usuário (nome, e-mail, senha, papel). Restrito a GESTOR."""
    repo = UsuarioRepository(db)
    if await repo.buscar_por_email(payload.email):
        raise HTTPException(status_code=400, detail="Já existe um usuário com este e-mail.")

    novo = await repo.criar(
        nome=payload.nome,
        email=payload.email,
        senha=payload.senha,
        papel=payload.papel,
        autor=usuario.email,
    )
    return UsuarioResponse.model_validate(novo)


@router.put("/{usuario_id}", response_model=UsuarioResponse)
async def atualizar_usuario(
    usuario_id: str,
    payload: UsuarioUpdate,
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Atualiza nome, papel e/ou senha de um usuário existente. Restrito a GESTOR."""
    repo = UsuarioRepository(db)
    encontrado = await repo.buscar_por_id(usuario_id)
    if not encontrado or encontrado.excluido:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    atualizado = await repo.atualizar(
        encontrado,
        autor=usuario.email,
        nome=payload.nome,
        papel=payload.papel,
        senha=payload.senha,
    )
    return UsuarioResponse.model_validate(atualizado)


@router.delete("/{usuario_id}", status_code=status.HTTP_204_NO_CONTENT)
async def excluir_usuario(
    usuario_id: str,
    usuario: Usuario = Depends(require_gestor),
    db: AsyncSession = Depends(get_db),
):
    """Exclusão lógica (soft delete) de um usuário. Restrito a GESTOR."""
    repo = UsuarioRepository(db)
    encontrado = await repo.buscar_por_id(usuario_id)
    if not encontrado or encontrado.excluido:
        raise HTTPException(status_code=404, detail="Usuário não encontrado.")

    if encontrado.id == usuario.id:
        raise HTTPException(
            status_code=400, detail="Não é possível excluir o próprio usuário autenticado."
        )

    await repo.deletar_soft(encontrado, autor=usuario.email)
    return None
