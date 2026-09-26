"""add lab_l/lab_a/lab_b to colors — lưu Lab đo THẬT từ máy đo màu, ưu tiên
hơn hex_color khi so màu (Tìm màu giống), vì HEX 8-bit làm mất chi tiết Lab
gốc, nhất là vùng màu tối. NULL nếu màu chưa được đo bằng máy.

Revision ID: a28c1121fb2d
Revises: c61e57d23012
Create Date: 2026-09-26 15:15:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects.postgresql import REAL


# revision identifiers, used by Alembic.
revision = 'a28c1121fb2d'
down_revision = 'c61e57d23012'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('colors', sa.Column('lab_l', REAL(), nullable=True))
    op.add_column('colors', sa.Column('lab_a', REAL(), nullable=True))
    op.add_column('colors', sa.Column('lab_b', REAL(), nullable=True))


def downgrade():
    op.drop_column('colors', 'lab_b')
    op.drop_column('colors', 'lab_a')
    op.drop_column('colors', 'lab_l')
