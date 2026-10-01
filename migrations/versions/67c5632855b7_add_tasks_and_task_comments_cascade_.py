"""add tasks and task comments, cascade product movements

Revision ID: 67c5632855b7
Revises:
Create Date: 2026-10-01 11:32:30.505195

Nota: la revision es idempotente a proposito. En Railway/MySQL la fase `release:`
puede reintentarse y MySQL no tiene DDL transaccional, asi que una corrida
fallida puede dejar el esquema a medias. Cada bloque comprueba el estado real
antes de actuar en lugar de asumir el punto de partida.
"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '67c5632855b7'
down_revision = None
branch_labels = None
depends_on = None

FK_NAME = 'fk_stock_movements_product'
PRODUCT_COLUMN = 'product_id'


def _inspector():
    return sa.inspect(op.get_bind())


def _create_tasks():
    if _inspector().has_table('tasks'):
        op.execute('-- tasks ya existe, se omite su creacion')
        return
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


def _create_task_comments():
    if _inspector().has_table('task_comments'):
        op.execute('-- task_comments ya existe, se omite su creacion')
        return
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


def _product_fk():
    """Devuelve el nombre real de la FK stock_movements.product_id, o None."""
    insp = _inspector()
    if not insp.has_table('stock_movements'):
        return None
    for fk in insp.get_foreign_keys('stock_movements'):
        if fk['referred_table'] == 'products' and fk['constrained_columns'] == [PRODUCT_COLUMN]:
            return fk['name']
    return None


def _has_cascade(table, fk_name):
    for fk in _inspector().get_foreign_keys(table):
        if fk['name'] == fk_name:
            return (fk.get('options') or {}).get('ondelete', '').upper() == 'CASCADE'
    return False


def _cascade_product_movements():
    """
    Reescribe la FK de stock_movements.product_id con ON DELETE CASCADE.
    Alembic no detecta cambios de ondelete, por eso se hace a mano y se busca el
    nombre real de la constraint (puede diferir entre instalaciones).
    """
    if not _inspector().has_table('stock_movements'):
        op.execute('-- stock_movements no existe, se omite la cascada')
        return

    current = _product_fk()
    if current == FK_NAME:
        op.execute('-- la FK ya tiene el nombre definitivo')
    elif current is not None:
        op.drop_constraint(current, 'stock_movements', type_='foreignkey')

    if _has_cascade('stock_movements', FK_NAME):
        op.execute('-- la cascada ya estaba aplicada')
        return

    op.create_foreign_key(
        FK_NAME, 'stock_movements', 'products', [PRODUCT_COLUMN], ['id'],
        ondelete='CASCADE'
    )


def upgrade():
    _create_tasks()
    _create_task_comments()
    _cascade_product_movements()


def downgrade():
    if _inspector().has_table('stock_movements'):
        current = _product_fk()
        if current == FK_NAME:
            op.drop_constraint(FK_NAME, 'stock_movements', type_='foreignkey')
            op.create_foreign_key(
                current, 'stock_movements', 'products', [PRODUCT_COLUMN], ['id']
            )

    if _inspector().has_table('task_comments'):
        op.drop_table('task_comments')
    if _inspector().has_table('tasks'):
        op.drop_table('tasks')
