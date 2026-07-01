from pydantic import BaseModel, ConfigDict
from typing import Literal

class UsuarioPermissaoResponse(BaseModel):
    usuario_id_externo: str
    papel: Literal["GESTOR", "CONSULTOR"]

    model_config = ConfigDict(from_attributes=True)
