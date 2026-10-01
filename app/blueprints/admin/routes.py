from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from sqlalchemy.exc import IntegrityError
from app.extensions import db
from app.models import Product, Category, User, StockMovement, Notification
from app.utils.decorators import admin_required

admin_bp = Blueprint('admin', __name__)

# Aplicamos los decoradores globales para todo el blueprint
@admin_bp.before_request
@login_required
@admin_required
def admin_protect():
    """Garantiza que ninguna ruta de este Blueprint sea accesible sin rol de Administrador."""
    pass


# -------------------------------------------------------------------
# GESTIÓN DE PRODUCTOS Y AJUSTES
# -------------------------------------------------------------------

@admin_bp.route('/product/new', methods=['GET', 'POST'])
def new_product():
    categories = Category.query.filter_by(establishment_id=current_user.establishment_id).all()

    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        category_id = request.form.get('category_id', type=int)
        initial_stock = request.form.get('current_stock', type=int, default=0)
        min_stock = request.form.get('min_stock', type=int, default=0)

        if not name or not category_id:
            flash('El nombre y la categoría son campos obligatorios.', 'danger')
            return render_template('admin/new_product.html', categories=categories)

        # 1. Crear el nuevo producto
        product = Product(
            establishment_id=current_user.establishment_id,
            category_id=category_id,
            name=name,
            current_stock=initial_stock,
            min_stock=min_stock
        )
        db.session.add(product)
        db.session.flush()  # Obtiene el ID generado para el producto

        # 2. Registrar el movimiento inicial si ingresó con stock
        if initial_stock > 0:
            movement = StockMovement(
                product_id=product.id,
                user_id=current_user.id,
                movement_type='IN',
                quantity=initial_stock,
                reason='Carga inicial al crear el producto'
            )
            db.session.add(movement)

        # 3. Notificar a todos los usuarios del establecimiento sobre el nuevo producto
        users = User.query.filter_by(establishment_id=current_user.establishment_id).all()
        notification_msg = f'Se agregó un nuevo producto al catálogo: "{product.name}".'

        for u in users:
            notif = Notification(
                user_id=u.id,
                message=notification_msg
            )
            db.session.add(notif)

        db.session.commit()
        flash(f'Producto "{product.name}" creado con éxito y notificado a los usuarios.', 'success')
        return redirect(url_for('products.index'))

    return render_template('admin/new_product.html', categories=categories)


@admin_bp.route('/product/<int:product_id>/adjust', methods=['POST'])
def adjust_stock(product_id):
    product = Product.query.get_or_404(product_id)

    if product.establishment_id != current_user.establishment_id:
        flash('No podés modificar productos de otro establecimiento.', 'danger')
        return redirect(url_for('products.index'))

    new_stock = request.form.get('new_stock', type=int)
    reason = request.form.get('reason', '').strip()

    if new_stock is None or new_stock < 0 or not reason:
        flash('El nuevo stock debe ser válido y el motivo del ajuste es obligatorio.', 'danger')
        return redirect(url_for('products.index'))

    diff = new_stock - product.current_stock
    product.current_stock = new_stock

    # Registrar el ajuste con el motivo obligatorio
    movement = StockMovement(
        product_id=product.id,
        user_id=current_user.id,
        movement_type='ADJUSTMENT',
        quantity=diff,
        reason=reason
    )

    db.session.add(movement)
    db.session.commit()

    flash(f'Stock de "{product.name}" ajustado correctamente a {new_stock} unidades.', 'info')
    return redirect(url_for('products.index'))


@admin_bp.route('/product/<int:product_id>/delete', methods=['POST'])
def delete_product(product_id):
    product = Product.query.get_or_404(product_id)

    if product.establishment_id != current_user.establishment_id:
        flash('Acción no permitida.', 'danger')
        return redirect(url_for('products.index'))

    product_name = product.name
    movements_count = len(product.movements)

    try:
        # cascade='all, delete-orphan' + ondelete='CASCADE' en la FK:
        # se borran también los movimientos de stock del producto.
        db.session.delete(product)
        db.session.flush()

        # Avisar a los usuarios del establecimiento, como se hace al crear productos
        users = User.query.filter_by(establishment_id=current_user.establishment_id).all()
        for u in users:
            db.session.add(Notification(
                user_id=u.id,
                message=f'El producto "{product_name}" fue eliminado del catálogo.'
            ))

        db.session.commit()
    except IntegrityError:
        # Si algún registro dependiente no se limpiara, no debe devolver un 500
        db.session.rollback()
        flash(f'No se pudo eliminar "{product_name}" porque tiene registros asociados.', 'danger')
        return redirect(url_for('products.index'))

    if movements_count:
        flash(
            f'El producto "{product_name}" fue eliminado del catálogo junto con '
            f'su historial de {movements_count} movimiento(s).',
            'warning'
        )
    else:
        flash(f'El producto "{product_name}" fue eliminado del catálogo.', 'warning')

    return redirect(url_for('products.index'))


# -------------------------------------------------------------------
# GESTIÓN DE CATEGORÍAS
# -------------------------------------------------------------------

@admin_bp.route('/categories', methods=['GET', 'POST'])
def categories():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        if name:
            # Evitar duplicados
            existing = Category.query.filter_by(
                establishment_id=current_user.establishment_id, 
                name=name
            ).first()

            if not existing:
                category = Category(
                    establishment_id=current_user.establishment_id,
                    name=name
                )
                db.session.add(category)
                db.session.commit()
                flash(f'Categoría "{name}" agregada.', 'success')
            else:
                flash('Esa categoría ya existe.', 'warning')
        else:
            flash('Ingresá un nombre válido para la categoría.', 'danger')

    categories_list = Category.query.filter_by(establishment_id=current_user.establishment_id).all()
    return render_template('admin/categories.html', categories=categories_list)


@admin_bp.route('/category/<int:category_id>/delete', methods=['POST'])
def delete_category(category_id):
    category = Category.query.get_or_404(category_id)

    if category.establishment_id != current_user.establishment_id:
        flash('Acción no permitida.', 'danger')
        return redirect(url_for('admin.categories'))

    category_name = category.name

    # products.category_id es NOT NULL, así que no se puede dejar la categoría
    # huérfana: se bloquea el borrado mientras tenga insumos asociados.
    products_count = Product.query.filter_by(category_id=category.id).count()

    if products_count > 0:
        plural = 'insumo' if products_count == 1 else 'insumos'
        flash(
            f'No se puede eliminar la categoría "{category_name}" porque tiene '
            f'{products_count} {plural} asociado(s). Reasigná esos insumos a otra '
            f'categoría o eliminalos primero.',
            'danger'
        )
        return redirect(url_for('admin.categories'))

    try:
        db.session.delete(category)
        db.session.commit()
    except IntegrityError:
        db.session.rollback()
        flash(f'No se pudo eliminar la categoría "{category_name}".', 'danger')
        return redirect(url_for('admin.categories'))

    flash(f'Categoría "{category_name}" eliminada.', 'warning')
    return redirect(url_for('admin.categories'))


# -------------------------------------------------------------------
# GESTIÓN DE USUARIOS
# -------------------------------------------------------------------

@admin_bp.route('/users', methods=['GET', 'POST'])
def users():
    if request.method == 'POST':
        username = request.form.get('username', '').strip()
        password = request.form.get('password', '')
        role = request.form.get('role', 'common')

        if not username or not password:
            flash('Usuario y contraseña son requeridos.', 'danger')
        elif User.query.filter_by(username=username).first():
            flash('El nombre de usuario ya está registrado.', 'warning')
        else:
            new_user = User(
                establishment_id=current_user.establishment_id,
                username=username,
                role=role
            )
            new_user.set_password(password)
            db.session.add(new_user)
            db.session.commit()
            flash(f'Usuario "{username}" creado con éxito.', 'success')

    users_list = User.query.filter_by(establishment_id=current_user.establishment_id).all()
    return render_template('admin/users.html', users=users_list)


@admin_bp.route('/users/<int:user_id>/delete', methods=['POST'])
def delete_user(user_id):
    if user_id == current_user.id:
        flash('No podés eliminar tu propio usuario en uso.', 'danger')
        return redirect(url_for('admin.users'))

    user = User.query.get_or_404(user_id)
    if user.establishment_id != current_user.establishment_id:
        flash('Acción no permitida.', 'danger')
        return redirect(url_for('admin.users'))

    username = user.username
    db.session.delete(user)
    db.session.commit()

    flash(f'Usuario "{username}" eliminado.', 'info')
    return redirect(url_for('admin.users'))