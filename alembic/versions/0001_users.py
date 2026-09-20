"""Baseline del modelo User de la actividad anterior."""
from alembic import op
import sqlalchemy as sa
revision = "0001_users"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    op.create_table('users',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('name', sa.String(length=80), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('role', sa.String(length=20), nullable=False),
    sa.Column('is_active', sa.Boolean(), nullable=False),
    sa.Column('internal_notes', sa.String(length=255), nullable=False),
    sa.CheckConstraint("role IN ('admin', 'support', 'user')", name='ck_users_role_allowed'),
    sa.CheckConstraint('length(email) <= 254', name='ck_users_email_max_length'),
    sa.CheckConstraint('length(name) <= 80', name='ck_users_name_max_length'),
    sa.CheckConstraint('length(trim(name)) >= 3', name='ck_users_name_min_length'),
    sa.PrimaryKeyConstraint('id')
    )
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.create_index(batch_op.f('ix_users_email'), ['email'], unique=True)
        batch_op.create_index(batch_op.f('ix_users_id'), ['id'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_is_active'), ['is_active'], unique=False)
        batch_op.create_index(batch_op.f('ix_users_role'), ['role'], unique=False)


def downgrade():
    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_users_role'))
        batch_op.drop_index(batch_op.f('ix_users_is_active'))
        batch_op.drop_index(batch_op.f('ix_users_id'))
        batch_op.drop_index(batch_op.f('ix_users_email'))

    op.drop_table('users')
