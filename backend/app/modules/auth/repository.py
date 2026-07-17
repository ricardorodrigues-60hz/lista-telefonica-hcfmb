import uuid
from datetime import datetime, timezone
from typing import Optional

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from app.modules.auth.models import RefreshToken


def _now_naive_utc() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


class RefreshTokenRepository:
    """Repository responsável pela persistência das sessões de refresh token.

    Habilita rotação (o token usado é revogado e substituído por um novo) e
    revogação explícita (logout), além de detecção de reuso de token já
    rotacionado — um indício de token roubado/comprometido.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def criar(self, usuario_id: str, token_hash: str, expira_em: datetime) -> RefreshToken:
        if expira_em.tzinfo is not None:
            expira_em = expira_em.astimezone(timezone.utc).replace(tzinfo=None)

        registro = RefreshToken(
            id=str(uuid.uuid4()),
            usuario_id=usuario_id,
            token_hash=token_hash,
            expira_em=expira_em,
        )
        self.db.add(registro)
        await self.db.commit()
        await self.db.refresh(registro)
        return registro

    async def buscar_por_hash(self, token_hash: str) -> Optional[RefreshToken]:
        result = await self.db.execute(
            select(RefreshToken).where(RefreshToken.token_hash == token_hash)
        )
        return result.scalars().first()

    def esta_valido(self, registro: RefreshToken) -> bool:
        if registro.revogado:
            return False
        return registro.expira_em > _now_naive_utc()

    async def revogar_por_token(self, token_hash: str) -> bool:
        registro = await self.buscar_por_hash(token_hash)
        if not registro:
            return False
        registro.revogado = True
        await self.db.commit()
        return True

    async def revogar_todos_do_usuario(self, usuario_id: str) -> None:
        result = await self.db.execute(
            select(RefreshToken).where(
                RefreshToken.usuario_id == usuario_id, RefreshToken.revogado == False
            )
        )
        for registro in result.scalars().all():
            registro.revogado = True
        await self.db.commit()

    async def rotacionar(self, registro_antigo: RefreshToken, novo_registro_id: str) -> None:
        """Marca o token antigo como revogado e aponta para o novo (cadeia de rotação)."""
        registro_antigo.revogado = True
        registro_antigo.substituido_por_id = novo_registro_id
        await self.db.commit()
