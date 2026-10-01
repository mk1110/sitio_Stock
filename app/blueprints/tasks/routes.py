from datetime import datetime, date

from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError

from app.extensions import db
from app.models import Task, TaskComment, User, Notification
from app.utils.decorators import admin_required

tasks_bp = Blueprint('tasks', __name__)

# Pares (valor, etiqueta) para los <select> de la interfaz
TASK_STATUS_CHOICES = [(v, Task.STATUS_LABELS[v]) for v in Task.STATUSES]
TASK_PRIORITY_CHOICES = [(v, Task.PRIORITY_LABELS[v]) for v in Task.PRIORITIES]


# -------------------------------------------------------------------
# HELPERS
# -------------------------------------------------------------------

def get_task_or_deny(task_id):
    """
    Devuelve la tarea si el usuario actual tiene permiso sobre ella.

    - 404 si la tarea no existe o pertenece a otro establecimiento (no filtramos
      información de otros tenants).
    - None (con flash) si el usuario no es el asignado ni es admin.
    """
    task = Task.query.get_or_404(task_id)

    if task.establishment_id != current_user.establishment_id:
        abort(404)

    if not (current_user.is_admin or task.assigned_to_id == current_user.id):
        flash('No tenés permisos para acceder a esa tarea.', 'danger')
        return None

    return task


def notify_users(user_ids, message):
    """Genera una notificación para cada usuario indicado (sin duplicados)."""
    for user_id in set(user_ids):
        db.session.add(Notification(user_id=user_id, message=message))


# -------------------------------------------------------------------
# LISTADO Y DETALLE
# -------------------------------------------------------------------

@tasks_bp.route('/tasks', methods=['GET'])
@login_required
def index():
    status = request.args.get('status', '').strip().upper()
    priority = request.args.get('priority', '').strip().upper()
    search_query = request.args.get('q', '').strip()
    show_done = request.args.get('done') == '1'

    # El admin ve todas las tareas del establecimiento; el resto, solo las suyas
    query = Task.query.filter_by(establishment_id=current_user.establishment_id)
    if not current_user.is_admin:
        query = query.filter_by(assigned_to_id=current_user.id)

    if status in Task.STATUSES:
        query = query.filter_by(status=status)
    elif not show_done:
        # Por defecto se ocultan las completadas para no tapar el trabajo pendiente
        query = query.filter(Task.status != 'DONE')

    if priority in Task.PRIORITIES:
        query = query.filter_by(priority=priority)

    if search_query:
        query = query.filter(
            db.or_(
                Task.title.ilike(f"%{search_query}%"),
                Task.description.ilike(f"%{search_query}%")
            )
        )

    # Las vencidas primero, luego por fecha límite y por fecha de asignación
    tasks = query.order_by(
        Task.due_date.is_(None), Task.due_date.asc(), Task.assigned_at.desc()
    ).all()

    # Listado del personal para el formulario de alta (solo lo usa el admin)
    staff = User.query.filter_by(
        establishment_id=current_user.establishment_id
    ).order_by(User.username.asc()).all()

    # Contadores para el resumen superior
    base = Task.query.filter_by(establishment_id=current_user.establishment_id)
    if not current_user.is_admin:
        base = base.filter_by(assigned_to_id=current_user.id)

    counters = {
        'total': base.count(),
        'pending': base.filter(Task.status == 'PENDING').count(),
        'in_progress': base.filter(Task.status == 'IN_PROGRESS').count(),
        'done': base.filter(Task.status == 'DONE').count(),
        'overdue': base.filter(Task.status != 'DONE', Task.due_date < date.today()).count(),
    }

    return render_template(
        'tasks/index.html',
        tasks=tasks,
        staff=staff,
        counters=counters,
        selected_status=status,
        selected_priority=priority,
        search_query=search_query,
        show_done=show_done,
        task_status_choices=TASK_STATUS_CHOICES,
        task_priority_choices=TASK_PRIORITY_CHOICES
    )


@tasks_bp.route('/tasks/', methods=['GET'])
@login_required
def index_slash():
    """Alias tolerante: /tasks/ redirige a la URL canónica /tasks."""
    return redirect(url_for('tasks.index', **request.args))


@tasks_bp.route('/tasks/<int:task_id>')
@login_required
def detail(task_id):
    task = get_task_or_deny(task_id)
    if task is None:
        return redirect(url_for('tasks.index'))

    return render_template(
        'tasks/detail.html',
        task=task,
        task_comments_max_length=TaskComment.MAX_LENGTH
    )


# -------------------------------------------------------------------
# ALTA DE TAREAS (solo administrador)
# -------------------------------------------------------------------

@tasks_bp.route('/tasks/create', methods=['POST'])
@admin_required
def create_task():
    title = request.form.get('title', '').strip()
    description = request.form.get('description', '').strip()
    priority = request.form.get('priority', 'MEDIUM').strip().upper()
    due_date_str = request.form.get('due_date', '').strip()
    assigned_to_id = request.form.get('assigned_to_id', type=int)

    # --- Validaciones ---
    if not title:
        flash('El título de la tarea es obligatorio.', 'danger')
        return redirect(url_for('tasks.index'))

    if priority not in Task.PRIORITIES:
        flash('La prioridad seleccionada no es válida.', 'danger')
        return redirect(url_for('tasks.index'))

    # El usuario asignado debe pertenecer al mismo establecimiento
    assignee = None
    if assigned_to_id:
        assignee = User.query.get(assigned_to_id)
        if not assignee or assignee.establishment_id != current_user.establishment_id:
            flash('El personal seleccionado no es válido.', 'danger')
            return redirect(url_for('tasks.index'))

    due_date = None
    if due_date_str:
        try:
            due_date = datetime.strptime(due_date_str, '%Y-%m-%d').date()
        except ValueError:
            flash('La fecha límite tiene un formato inválido.', 'danger')
            return redirect(url_for('tasks.index'))

        if due_date < date.today():
            flash('La fecha límite no puede ser anterior a hoy.', 'danger')
            return redirect(url_for('tasks.index'))

    if not assignee:
        flash('Debés asignar la tarea a una persona del personal.', 'danger')
        return redirect(url_for('tasks.index'))

    # --- Alta ---
    task = Task(
        establishment_id=current_user.establishment_id,
        title=title,
        description=description or None,
        priority=priority,
        due_date=due_date,
        status='PENDING',
        assigned_to_id=assignee.id,
        created_by_id=current_user.id
    )

    try:
        db.session.add(task)
        db.session.flush()

        notify_users(
            [assignee.id],
            f'Nueva tarea asignada: "{task.title}".'
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('No se pudo crear la tarea por un error de integridad en la base.', 'danger')
        return redirect(url_for('tasks.index'))

    flash(f'Tarea "{task.title}" creada y asignada a {assignee.username}.', 'success')
    return redirect(url_for('tasks.detail', task_id=task.id))


# -------------------------------------------------------------------
# CAMBIO DE ESTADO
# -------------------------------------------------------------------

@tasks_bp.route('/tasks/<int:task_id>/status', methods=['POST'])
@login_required
def update_status(task_id):
    task = get_task_or_deny(task_id)
    if task is None:
        return redirect(url_for('tasks.index'))

    new_status = request.form.get('status', '').strip().upper()

    if new_status not in Task.STATUSES:
        flash('El estado indicado no es válido.', 'danger')
        return redirect(url_for('tasks.detail', task_id=task.id))

    if new_status == task.status:
        flash('La tarea ya se encuentra en ese estado.', 'warning')
        return redirect(url_for('tasks.detail', task_id=task.id))

    old_status = task.status
    task.status = new_status
    # Se registra (o se limpia) la fecha de finalización según el nuevo estado
    task.completed_at = datetime.utcnow() if new_status == 'DONE' else None

    try:
        # Se avisa al creador y al asignado, salvo a quien hizo el cambio
        recipients = {task.created_by_id, task.assigned_to_id} - {current_user.id}
        notify_users(
            recipients,
            f'La tarea "{task.title}" pasó de '
            f'"{Task.STATUS_LABELS[old_status]}" a "{Task.STATUS_LABELS[new_status]}".'
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('No se pudo actualizar el estado de la tarea.', 'danger')
        return redirect(url_for('tasks.detail', task_id=task.id))

    flash(f'Estado actualizado a "{Task.STATUS_LABELS[new_status]}".', 'info')
    return redirect(url_for('tasks.detail', task_id=task.id))


# -------------------------------------------------------------------
# COMENTARIOS / OBSERVACIONES
# -------------------------------------------------------------------

@tasks_bp.route('/tasks/<int:task_id>/comments', methods=['POST'])
@login_required
def add_comment(task_id):
    task = get_task_or_deny(task_id)
    if task is None:
        return redirect(url_for('tasks.index'))

    body = request.form.get('body', '').strip()

    if not body:
        flash('El comentario no puede estar vacío.', 'warning')
        return redirect(url_for('tasks.detail', task_id=task.id))

    if len(body) > TaskComment.MAX_LENGTH:
        flash(f'El comentario no puede superar los {TaskComment.MAX_LENGTH} caracteres.', 'warning')
        return redirect(url_for('tasks.detail', task_id=task.id))

    comment = TaskComment(
        task_id=task.id,
        user_id=current_user.id,
        body=body
    )

    try:
        db.session.add(comment)
        db.session.flush()

        # Se avisa al creador y al asignado, salvo a quien escribió el comentario
        recipients = {task.created_by_id, task.assigned_to_id} - {current_user.id}
        notify_users(
            recipients,
            f'{current_user.username} comentó en la tarea "{task.title}": '
            f'"{body[:120]}{"..." if len(body) > 120 else ""}"'
        )
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('No se pudo guardar el comentario.', 'danger')
        return redirect(url_for('tasks.detail', task_id=task.id))

    flash('Comentario agregado.', 'success')
    return redirect(url_for('tasks.detail', task_id=task.id))


@tasks_bp.route('/tasks/<int:task_id>/comments/<int:comment_id>/delete', methods=['POST'])
@login_required
def delete_comment(task_id, comment_id):
    task = get_task_or_deny(task_id)
    if task is None:
        return redirect(url_for('tasks.index'))

    comment = TaskComment.query.get_or_404(comment_id)

    # El comentario tiene que pertenecer a la tarea de la URL
    if comment.task_id != task.id:
        abort(404)

    # Sólo el autor del comentario o un administrador pueden borrarlo
    if comment.user_id != current_user.id and not current_user.is_admin:
        flash('Sólo podés eliminar tus propios comentarios.', 'danger')
        return redirect(url_for('tasks.detail', task_id=task.id))

    try:
        db.session.delete(comment)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('No se pudo eliminar el comentario.', 'danger')
        return redirect(url_for('tasks.detail', task_id=task.id))

    flash('Comentario eliminado.', 'warning')
    return redirect(url_for('tasks.detail', task_id=task.id))


# -------------------------------------------------------------------
# ELIMINACIÓN DE TAREAS (solo administrador)
# -------------------------------------------------------------------

@tasks_bp.route('/tasks/<int:task_id>/delete', methods=['POST'])
@admin_required
def delete_task(task_id):
    task = get_task_or_deny(task_id)
    if task is None:
        return redirect(url_for('tasks.index'))

    title = task.title
    comments_count = len(task.comments)

    try:
        # cascade='all, delete-orphan' + ondelete='CASCADE' limpian el hilo de comentarios
        db.session.delete(task)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash('No se pudo eliminar la tarea. Revisá si tiene comentarios asociados.', 'danger')
        return redirect(url_for('tasks.index'))

    extra = f' y sus {comments_count} comentario(s)' if comments_count else ''
    flash(f'Tarea "{title}" eliminada{extra}.', 'warning')
    return redirect(url_for('tasks.index'))
