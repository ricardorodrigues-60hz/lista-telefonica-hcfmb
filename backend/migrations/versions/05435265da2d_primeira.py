"""primeira

Revision ID: 05435265da2d
Revises: 
Create Date: 2026-06-23 11:02:21.317348

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '05435265da2d'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    
    op.create_table(
        'usuario',
        sa.Column('id', sa.Integer)
    )
    
    


def downgrade() -> None:
    """Downgrade schema."""

    op.drop_table('usuarios')
