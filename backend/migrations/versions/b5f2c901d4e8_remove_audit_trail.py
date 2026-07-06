"""remove_audit_trail

Revision ID: b5f2c901d4e8
Revises: a36a895e7353
Create Date: 2026-07-06 18:04:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b5f2c901d4e8'
down_revision: Union[str, Sequence[str], None] = 'a36a895e7353'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Remove a tabela audit_trail — sistema de auditoria descontinuado."""
    op.drop_index(op.f('ix_audit_trail_id'), table_name='audit_trail')
    op.drop_table('audit_trail')


def downgrade() -> None:
    """Recria a tabela audit_trail caso necessário reverter."""
    op.create_table(
        'audit_trail',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('usuario_nome', sa.String(), nullable=False),
        sa.Column('acao', sa.String(), nullable=False),
        sa.Column('contato_id', sa.String(), nullable=True),
        sa.Column('detalhes', sa.String(), nullable=False),
        sa.Column(
            'criado_em',
            sa.DateTime(timezone=True),
            server_default=sa.text('(CURRENT_TIMESTAMP)'),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_audit_trail_id'), 'audit_trail', ['id'], unique=False)
