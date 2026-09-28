from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('products.index'))

    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')

        if not username or not password:
            flash('Por favor, completá todos los campos.', 'danger')
            return render_template('auth/login.html')

        user = User.query.filter_by(username=username).first()

        # Validar usuario y contraseña mediante el método check_password de nuestro modelo
        if user and user.check_password(password):
            login_user(user)
            flash(f'¡Bienvenido/a, {user.username}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('products.index'))
        else:
            flash('Usuario o contraseña incorrectos.', 'danger')

    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Sesión cerrada correctamente.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        # Validaciones del lado del servidor
        if not current_password or not new_password or not confirm_password:
            flash('Todos los campos son obligatorios.', 'warning')
            return render_template('auth/change_password.html')

        if not current_user.check_password(current_password):
            flash('La contraseña actual es incorrecta.', 'danger')
            return render_template('auth/change_password.html')

        if new_password != confirm_password:
            flash('Las nuevas contraseñas no coinciden.', 'danger')
            return render_template('auth/change_password.html')

        if len(new_password) < 6:
            flash('La nueva contraseña debe tener al menos 6 caracteres.', 'warning')
            return render_template('auth/change_password.html')

        # Actualizar la contraseña
        current_user.set_password(new_password)
        db.session.commit()

        flash('Tu contraseña ha sido actualizada con éxito.', 'success')
        return redirect(url_for('products.index'))

    return render_template('auth/change_password.html')