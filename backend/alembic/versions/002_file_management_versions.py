"""File management and versioning migration

Revision ID: 002_file_management_versions
Revises: 001_initial_schema
Create Date: 2026-10-26 21:50:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa

revision: str = '002_file_management_versions'
down_revision: Union[str, None] = '001_initial_schema'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # 1. files updates: status and category
    op.add_column('files', sa.Column('status', sa.String(length=32), server_default='ready', nullable=False))
    op.add_column('files', sa.Column('category', sa.String(length=64), nullable=True))
    op.create_index(op.f('ix_files_category'), 'files', ['category'], unique=False)

    # 2. folders updates: parent_id
    op.add_column('folders', sa.Column('parent_id', sa.Integer(), nullable=True))
    with op.batch_alter_table('folders') as batch_op:
        batch_op.create_foreign_key('fk_folders_parent_id', 'folders', ['parent_id'], ['id'], ondelete='CASCADE')
    op.create_index(op.f('ix_folders_parent_id'), 'folders', ['parent_id'], unique=False)

    # 3. file_keys updates: file_version
    op.add_column('file_keys', sa.Column('file_version', sa.Integer(), server_default='1', nullable=False))

    # 4. create file_versions table
    op.create_table(
        'file_versions',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('file_id', sa.Integer(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('storage_key', sa.String(length=255), nullable=False),
        sa.Column('size', sa.Integer(), nullable=False),
        sa.Column('sha256', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['file_id'], ['files.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_file_versions_id'), 'file_versions', ['id'], unique=False)
    op.create_index(op.f('ix_file_versions_file_id'), 'file_versions', ['file_id'], unique=False)

def downgrade() -> None:
    op.drop_index(op.f('ix_file_versions_file_id'), table_name='file_versions')
    op.drop_index(op.f('ix_file_versions_id'), table_name='file_versions')
    op.drop_table('file_versions')

    op.drop_column('file_keys', 'file_version')

    op.drop_index(op.f('ix_folders_parent_id'), table_name='folders')
    with op.batch_alter_table('folders') as batch_op:
        batch_op.drop_constraint('fk_folders_parent_id', type_='foreignkey')
    op.drop_column('folders', 'parent_id')

    op.drop_index(op.f('ix_files_category'), table_name='files')
    op.drop_column('files', 'category')
    op.drop_column('files', 'status')
