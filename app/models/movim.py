from datetime import datetime
from app.extensions import db

class StockMovement(db.Model):
    __tablename__ = 'stock_movements'

    id = db.Column(db.Integer, primary_key=True)
    # ondelete='CASCADE' garantiza en la base que el historial se borre junto al producto
    product_id = db.Column(db.Integer, db.ForeignKey('products.id', ondelete='CASCADE'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    movement_type = db.Column(db.Enum('IN', 'OUT', 'ADJUSTMENT', name='movement_types'), nullable=False)
    quantity = db.Column(db.Integer, nullable=False)
    reason = db.Column(db.Text, nullable=True)  # Campo obligatorio para ajustes del admin
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


class Notification(db.Model):
    __tablename__ = 'notifications'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    message = db.Column(db.String(255), nullable=False)
    is_read = db.Column(db.Boolean, nullable=False, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)