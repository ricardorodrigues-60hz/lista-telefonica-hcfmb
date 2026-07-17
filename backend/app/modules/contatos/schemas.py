"""Contact schemas with validation.

Includes lightweight validators to normalize phone numbers.
"""

from __future__ import annotations

import datetime
import re
from enum import Enum
from typing import Optional
from uuid import UUID

from pydantic import (
    BaseModel,
    ConfigDict,
    EmailStr,
    field_validator,
)


class TipoNumero(str, Enum):
    INSTITUCIONAL = "institucional"
    PUBLICO = "publico"


class ContatoBase(BaseModel):
    nome: str
    telefone: str
    email: Optional[EmailStr] = None
    tipo_numero: TipoNumero = TipoNumero.PUBLICO

    @field_validator("telefone")
    def validate_telefone(cls, v: str) -> str:  # type: ignore[override]
        # Accept common phone characters but reject letters
        if not re.match(r"^[0-9\+\(\)\s\-\.]+$", v):
            raise ValueError("telefone inválido")
        digits = re.sub(r"\D", "", v)
        if len(digits) < 8:
            raise ValueError("telefone inválido")
        return v


class ContatoUpdate(BaseModel):
    nome: Optional[str] = None
    telefone: Optional[str] = None
    email: Optional[EmailStr] = None
    tipo_numero: Optional[TipoNumero] = None


class ContatoResponse(ContatoBase):
    id: UUID
    criado_em: Optional[datetime.datetime] = None
    atualizado_em: datetime.datetime
    excluido: bool = False

    model_config = ConfigDict(from_attributes=True)
