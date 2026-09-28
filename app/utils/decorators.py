from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 1. Verificar si el usuario inició sesión
        if not current_user.is_authenticated:
            flash('Por favor, iniciá sesión para acceder a esta página.', 'warning')
            return redirect(url_for('auth.login'))
        
        # 2. Verificar si el usuario tiene el rol de administrador
        if not current_user.is_admin:
            flash('Acceso denegado. Se requieren permisos de administrador.', 'danger')
            return redirect(url_for('products.index'))
            
        return f(*args, **kwargs)
    return decorated_function