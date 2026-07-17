from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.modules.usuarios.models import Usuario
from app.modules.auth.service import require_consultor
from app.modules.sync.schemas import SyncPayload, SyncResponse
from app.modules.sync.service import SyncService

router = APIRouter(tags=["Sincronização"])


@router.post("", response_model=SyncResponse)
async def sync_contatos(
    payload: SyncPayload,
    usuario: Usuario = Depends(require_consultor),
    db: AsyncSession = Depends(get_db),
):
    """Sincronização bidirecional/offline dos contatos (Dexie.js -> backend)."""
    service = SyncService(db)
    return await service.sincronizar(payload, usuario.email)
