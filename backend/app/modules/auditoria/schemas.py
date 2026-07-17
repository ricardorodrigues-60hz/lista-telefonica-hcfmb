"""Schemas de leitura da trilha de auditoria."""

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict


class AuditTrailResponse(BaseModel):
    id: int
    usuario_nome: str
    acao: str
    tabela: str
    registro_id: Optional[str] = None
    detalhes: str
    dados_modificados: Optional[str] = None
    criado_em: datetime

    model_config = ConfigDict(from_attributes=True)
