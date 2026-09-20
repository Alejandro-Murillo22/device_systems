"""Añade contraseña privada sin modificar usuarios o préstamos existentes."""
from alembic import op
import sqlalchemy as sa

revision = "0003_user_password"
down_revision = "0d0e8b654860"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("users", sa.Column("hashed_password", sa.String(255), nullable=True))


def downgrade():
    # DROP COLUMN nativo evita reconstruir users y romper FK del historial en SQLite.
    op.drop_column("users", "hashed_password")
