"""autenticacao_jwt_email_senha

Substitui o modelo de "usuário confiado por ID externo" por autenticação
própria com e-mail + senha, e adiciona a tabela `refresh_tokens` para
suportar rotação/revogação real de sessões. Também generaliza `audit_trail`
para cobrir múltiplas tabelas (contatos, usuários).

Revision ID: f3a8c1d92b7e
Revises: a36a895e7353
Create Date: 2026-07-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f3a8c1d92b7e'
down_revision: Union[str, Sequence[str], None] = 'a36a895e7353'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # --- audit_trail: generaliza para múltiplas tabelas ---
    with op.batch_alter_table('audit_trail', schema=None) as batch_op:
        batch_op.alter_column('contato_id', new_column_name='registro_id')
        batch_op.add_column(sa.Column('tabela', sa.String(), nullable=False, server_default='contatos'))
        batch_op.add_column(sa.Column('dados_modificados', sa.String(), nullable=True))

    # --- usuarios: modelo antigo (usuario_id_externo/papel) é substituído por
    # e-mail + senha_hash. Como a PK muda (de usuario_id_externo para id UUID),
    # a tabela é recriada; não há dados de senha para migrar automaticamente.
    op.drop_index(op.f('ix_usuarios_usuario_id_externo'), table_name='usuarios')
    op.drop_table('usuarios')

    op.create_table(
        'usuarios',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('nome', sa.String(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('senha_hash', sa.String(), nullable=False),
        sa.Column('papel', sa.String(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('atualizado_em', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('excluido', sa.Boolean(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_usuarios_email'), 'usuarios', ['email'], unique=True)

    # --- refresh_tokens: nova tabela para rotação/revogação de sessões ---
    op.create_table(
        'refresh_tokens',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('usuario_id', sa.String(length=36), nullable=False),
        sa.Column('token_hash', sa.String(), nullable=False),
        sa.Column('criado_em', sa.DateTime(timezone=True), server_default=sa.text('(CURRENT_TIMESTAMP)'), nullable=False),
        sa.Column('expira_em', sa.DateTime(timezone=True), nullable=False),
        sa.Column('revogado', sa.Boolean(), nullable=False),
        sa.Column('substituido_por_id', sa.String(length=36), nullable=True),
        sa.ForeignKeyConstraint(['usuario_id'], ['usuarios.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index(op.f('ix_refresh_tokens_usuario_id'), 'refresh_tokens', ['usuario_id'], unique=False)
    op.create_index(op.f('ix_refresh_tokens_token_hash'), 'refresh_tokens', ['token_hash'], unique=True)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_refresh_tokens_token_hash'), table_name='refresh_tokens')
    op.drop_index(op.f('ix_refresh_tokens_usuario_id'), table_name='refresh_tokens')
    op.drop_table('refresh_tokens')

    op.drop_index(op.f('ix_usuarios_email'), table_name='usuarios')
    op.drop_table('usuarios')

    op.create_table(
        'usuarios',
        sa.Column('usuario_id_externo', sa.String(), nullable=False),
        sa.Column('papel', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('usuario_id_externo'),
    )
    op.create_index(op.f('ix_usuarios_usuario_id_externo'), 'usuarios', ['usuario_id_externo'], unique=False)

    with op.batch_alter_table('audit_trail', schema=None) as batch_op:
        batch_op.drop_column('dados_modificados')
        batch_op.drop_column('tabela')
        batch_op.alter_column('registro_id', new_column_name='contato_id')
