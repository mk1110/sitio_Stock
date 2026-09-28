from datetime import datetime
from flask import Blueprint, render_template, request
from flask_login import login_required, current_user
from sqlalchemy import func, case
from app.extensions import db
from app.models import Product, StockMovement, Category

reports_bp = Blueprint('reports', __name__)

@reports_bp.route('/monthly')
@login_required
def monthly_report():
    now = datetime.now()
    
    # Obtener mes y año desde los parámetros de la URL, o usar el mes/año actual por defecto
    selected_month = request.args.get('month', type=int, default=now.month)
    selected_year = request.args.get('year', type=int, default=now.year)
    selected_category_id = request.args.get('category_id', type=int)

    # Consulta agrupada sobre la tabla de movimientos
    # Filtra por el establecimiento del usuario activo y el período seleccionado
    query = db.session.query(
        Product.id.label('product_id'),
        Product.name.label('product_name'),
        Category.name.label('category_name'),
        func.sum(case((StockMovement.movement_type == 'IN', StockMovement.quantity), else_=0)).label('total_in'),
        func.sum(case((StockMovement.movement_type == 'OUT', StockMovement.quantity), else_=0)).label('total_out'),
        func.count(StockMovement.id).label('total_movements')
    ).join(Product, StockMovement.product_id == Product.id)\
     .join(Category, Product.category_id == Category.id)\
     .filter(Product.establishment_id == current_user.establishment_id)\
     .filter(func.extract('month', StockMovement.created_at) == selected_month)\
     .filter(func.extract('year', StockMovement.created_at) == selected_year)

    if selected_category_id:
        query = query.filter(Product.category_id == selected_category_id)

    report_data = query.group_by(Product.id, Product.name, Category.name)\
                       .order_by(Product.name.asc()).all()

    # Totales generales del período
    grand_total_in = sum(item.total_in for item in report_data)
    grand_total_out = sum(item.total_out for item in report_data)

    categories = Category.query.filter_by(establishment_id=current_user.establishment_id).all()
    
    # Lista de años disponible para el selector (ej: desde 2025 hasta el año actual)
    years_list = list(range(now.year, 2024, -1))

    return render_template(
        'reports/monthly.html',
        report_data=report_data,
        categories=categories,
        selected_month=selected_month,
        selected_year=selected_year,
        selected_category_id=selected_category_id,
        grand_total_in=grand_total_in,
        grand_total_out=grand_total_out,
        years_list=years_list
    )