from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Product, Category, StockMovement, Notification

products_bp = Blueprint('products', __name__)

@products_bp.route('/')
@login_required
def index():
    # Obtener filtros de la URL (si existen)
    category_id = request.args.get('category_id', type=int)
    search_query = request.args.get('q', '').strip()

    # Consulta base filtrando por el establecimiento del usuario activo
    query = Product.query.filter_by(establishment_id=current_user.establishment_id)

    if category_id:
        query = query.filter_by(category_id=category_id)

    if search_query:
        query = query.filter(Product.name.ilike(f"%{search_query}%"))

    products = query.order_by(Product.name.asc()).all()
    categories = Category.query.filter_by(establishment_id=current_user.establishment_id).all()

    # Obtener notificaciones no leídas del usuario
    unread_notifications = Notification.query.filter_by(
        user_id=current_user.id, 
        is_read=False
    ).order_by(Notification.created_at.desc()).all()

    return render_template(
        'products/index.html', 
        products=products, 
        categories=categories,
        unread_notifications=unread_notifications,
        selected_category=category_id,
        search_query=search_query
    )


@products_bp.route('/product/<int:product_id>/update-stock', methods=['POST'])
@login_required
def update_stock(product_id):
    product = Product.query.get_or_404(product_id)

    # Verificar pertenencia al mismo establecimiento por seguridad
    if product.establishment_id != current_user.establishment_id:
        flash('No tenés permisos para modificar productos de otro establecimiento.', 'danger')
        return redirect(url_for('products.index'))

    action = request.form.get('action')  # 'add' o 'subtract'
    quantity_str = request.form.get('quantity', '0')

    try:
        quantity = int(quantity_str)
        if quantity <= 0:
            flash('La cantidad ingresada debe ser un número entero mayor a cero.', 'warning')
            return redirect(url_for('products.index'))
    except ValueError:
        flash('Por favor, ingresá un número válido.', 'warning')
        return redirect(url_for('products.index'))

    # Lógica de Negocio y Validaciones
    if action == 'add':
        product.current_stock += quantity
        movement_type = 'IN'
        flash_message = f'Se cargaron {quantity} unidad(es) a "{product.name}".'
        flash_category = 'success'

    elif action == 'subtract':
        # Requisito clave: Verificar existencia de stock suficiente
        if quantity > product.current_stock:
            flash(f'Stock insuficiente para "{product.name}". Stock disponible: {product.current_stock}.', 'danger')
            return redirect(url_for('products.index'))

        product.current_stock -= quantity
        movement_type = 'OUT'
        flash_message = f'Se descontaron {quantity} unidad(es) de "{product.name}".'
        flash_category = 'success'
    else:
        flash('Acción no válida.', 'danger')
        return redirect(url_for('products.index'))

    # Registrar el movimiento en el historial
    movement = StockMovement(
        product_id=product.id,
        user_id=current_user.id,
        movement_type=movement_type,
        quantity=quantity
    )

    db.session.add(movement)
    db.session.commit()

    flash(flash_message, flash_category)
    return redirect(url_for('products.index'))


@products_bp.route('/notifications/clear', methods=['POST'])
@login_required
def clear_notifications():
    """Marca todas las notificaciones del usuario como leídas."""
    Notification.query.filter_by(user_id=current_user.id, is_read=False).update({'is_read': True})
    db.session.commit()
    return redirect(url_for('products.index'))