"""add tasks and task comments, cascade product movements

Revision ID: 67c5632855b7
Revises: 
Create Date: 2026-10-01 11:32:30.505195

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67c5632855b7'
down_revision = None
branch_labels = None
depends_on = None

# Nombre real de la FK existente en MySQL (constraint autogenerado por InnoDB)
STOCK_MOVEMENTS_PRODUCT_FK = 'stock_movements_ibfk_1'
STOCK_MOVEMENTS_PRODUCT_FK_NEW = 'fk_stock_movements_product'


def upgrade():
    # --- Módulo de Tareas del Personal ---
    op.create_table(
        'tasks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('establishment_id', sa.Integer(), nullable=False),
        sa.Column('title', sa.String(length=150), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('status', sa.Enum('PENDING', 'IN_PROGRESS', 'DONE', name='task_statuses'), nullable=False),
        sa.Column('priority', sa.Enum('LOW', 'MEDIUM', 'HIGH', name='task_priorities'), nullable=False),
        sa.Column('due_date', sa.Date(), nullable=True),
        sa.Column('assigned_at', sa.DateTime(), nullable=True),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('assigned_to_id', sa.Integer(), nullable=False),
        sa.Column('created_by_id', sa.Integer(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['assigned_to_id'], ['users.id']),
        sa.ForeignKeyConstraint(['created_by_id'], ['users.id']),
        sa.ForeignKeyConstraint(['establishment_id'], ['establishments.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # --- Comentarios / observaciones de cada tarea ---
    op.create_table(
        'task_comments',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('task_id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('body', sa.Text(), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        # ondelete='CASCADE': borrar la tarea borra su hilo de comentarios
        sa.ForeignKeyConstraint(['task_id'], ['tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.PrimaryKeyConstraint('id')
    )

    # --- Borrado en cascada de insumos con su historial ---
    # Alembic no detecta cambios en ondelete, por eso se reescribe la FK a mano.
    op.drop_constraint(STOCK_MOVEMENTS_PRODUCT_FK, 'stock_movements', type_='foreignkey')
    op.create_foreign_key(
        STOCK_MOVEMENTS_PRODUCT_FK_NEW,
        'stock_movements',
        'products',
        ['product_id'],
        ['id'],
        ondelete='CASCADE'
    )


def downgrade():
    # Se restaura la FK original (sin cascada)
    op.drop_constraint(STOCK_MOVEMENTS_PRODUCT_FK_NEW, 'stock_movements', type_='foreignkey')
    op.create_foreign_key(
        STOCK_MOVEMENTS_PRODUCT_FK,
        'stock_movements',
        'products',
        ['product_id'],
        ['id']
    )

    op.drop_table('task_comments')
    op.drop_table('tasks')
