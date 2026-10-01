from datetime import datetime
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app.extensions import db, login_manager

class Establishment(db.Model):
    __tablename__ = 'establishments'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    address = db.Column(db.String(200), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    users = db.relationship('User', backref='establishment', lazy=True)
    categories = db.relationship('Category', backref='establishment', lazy=True)
    products = db.relationship('Product', backref='establishment', lazy=True)
    tasks = db.relationship('Task', backref='establishment', lazy=True)

class User(UserMixin, db.Model):
    __tablename__ = 'users'

    id = db.Column(db.Integer, primary_key=True)
    establishment_id = db.Column(db.Integer, db.ForeignKey('establishments.id'), nullable=False)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.Enum('admin', 'common', name='user_roles'), nullable=False, default='common')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Relaciones
    movements = db.relationship('StockMovement', backref='user', lazy=True)
    notifications = db.relationship('Notification', backref='user', lazy=True)

    # Tareas del Personal. Se especifican las foreign_keys porque Task referencia
    # a users.id dos veces (asignado_a / creado_por).
    # Sin cascade: reasignar una tarea no la borra ni le cambia el id, y la FK
    # impide borrar un usuario que tenga tareas asignadas.
    assigned_tasks = db.relationship(
        'Task',
        foreign_keys='Task.assigned_to_id',
        backref=db.backref('assignee', lazy=True),
        lazy=True
    )
    created_tasks = db.relationship(
        'Task',
        foreign_keys='Task.created_by_id',
        backref=db.backref('creator', lazy=True),
        lazy=True
    )
    task_comments = db.relationship('TaskComment', backref='user', lazy=True)

    # Métodos para manejo de contraseñas
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @property
    def is_admin(self):
        return self.role == 'admin'


# User loader para Flask-Login
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))