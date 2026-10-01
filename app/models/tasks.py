from datetime import datetime, date
from app.extensions import db


class Task(db.Model):
    __tablename__ = 'tasks'

    # Catálogos usados por la interfaz (valores en BD, etiquetas en español)
    STATUSES = ('PENDING', 'IN_PROGRESS', 'DONE')
    PRIORITIES = ('LOW', 'MEDIUM', 'HIGH')
    STATUS_LABELS = {
        'PENDING': 'Pendiente',
        'IN_PROGRESS': 'En Progreso',
        'DONE': 'Completada',
    }
    PRIORITY_LABELS = {
        'LOW': 'Baja',
        'MEDIUM': 'Media',
        'HIGH': 'Alta',
    }
    # Clases de Bootstrap para las etiquetas de la interfaz
    STATUS_BADGES = {
        'PENDING': 'bg-secondary',
        'IN_PROGRESS': 'bg-info text-dark',
        'DONE': 'bg-success',
    }
    PRIORITY_BADGES = {
        'LOW': 'bg-light text-dark border',
        'MEDIUM': 'bg-warning text-dark',
        'HIGH': 'bg-danger',
    }

    id = db.Column(db.Integer, primary_key=True)
    establishment_id = db.Column(db.Integer, db.ForeignKey('establishments.id'), nullable=False)
    title = db.Column(db.String(150), nullable=False)
    description = db.Column(db.Text, nullable=True)
    status = db.Column(db.Enum(*STATUSES, name='task_statuses'), nullable=False, default='PENDING')
    priority = db.Column(db.Enum(*PRIORITIES, name='task_priorities'), nullable=False, default='MEDIUM')
    due_date = db.Column(db.Date, nullable=True)  # Fecha límite, opcional
    assigned_at = db.Column(db.DateTime, default=datetime.utcnow)  # Fecha de asignación
    completed_at = db.Column(db.DateTime, nullable=True)
    assigned_to_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_by_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relaciones
    comments = db.relationship(
        'TaskComment',
        backref='task',
        lazy=True,
        cascade='all, delete-orphan'  # Al borrar la tarea se va su hilo de comentarios
    )

    @property
    def status_label(self):
        return self.STATUS_LABELS.get(self.status, self.status)

    @property
    def status_badge(self):
        return self.STATUS_BADGES.get(self.status, 'bg-secondary')

    @property
    def priority_label(self):
        return self.PRIORITY_LABELS.get(self.priority, self.priority)

    @property
    def priority_badge(self):
        return self.PRIORITY_BADGES.get(self.priority, 'bg-secondary')

    @property
    def is_overdue(self):
        """Devuelve True si la tarea sigue abierta y ya venció su fecha límite."""
        if self.due_date is None or self.status == 'DONE':
            return False
        return self.due_date < date.today()


class TaskComment(db.Model):
    __tablename__ = 'task_comments'

    MAX_LENGTH = 1000

    id = db.Column(db.Integer, primary_key=True)
    task_id = db.Column(
        db.Integer,
        db.ForeignKey('tasks.id', ondelete='CASCADE'),
        nullable=False
    )
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    body = db.Column(db.Text, nullable=False)  # Observación / comentario del usuario
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
