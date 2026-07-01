from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from app.core.database import Base

class UsuarioPermissao(Base):
    __tablename__ = "usuarios"

    usuario_id_externo: Mapped[str] = mapped_column(String, primary_key=True, index=True)
    papel: Mapped[str] = mapped_column(String, nullable=False, default="CONSULTOR")
