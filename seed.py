from app import create_app
from app.extensions import db
from app.models import Establishment, Category, User

app = create_app()

def seed_database():
    with app.app_context():
        print("🌱 Iniciando la carga de datos iniciales (Seed)...")

        # 1. Crear las tablas si aún no existen
        db.create_all()

        # 2. Crear Establecimiento inicial (incluyendo la dirección requerida)
        establishment = Establishment.query.filter_by(name="Hospital Central").first()
        if not establishment:
            establishment = Establishment(
                name="Hospital Central",
                address="Av. Córdoba 1234"  # <-- Agregamos la dirección obligatoria
            )
            db.session.add(establishment)
            db.session.flush()  # Obtiene el ID generado
            print(f"  ✓ Establecimiento '{establishment.name}' creado.")
        else:
            print(f"  ℹ️ El establecimiento '{establishment.name}' ya existía.")

        # 3. Crear las 5 Categorías predeterminadas
        default_categories = [
            "Medicamentos",
            "Descartables",
            "Insumos Quirúrgicos",
            "Laboratorio",
            "Limpieza e Higiene"
        ]

        for cat_name in default_categories:
            existing_cat = Category.query.filter_by(
                establishment_id=establishment.id,
                name=cat_name
            ).first()

            if not existing_cat:
                category = Category(
                    establishment_id=establishment.id,
                    name=cat_name
                )
                db.session.add(category)
                print(f"  ✓ Categoría '{cat_name}' agregada.")
            else:
                print(f"  ℹ️ La categoría '{cat_name}' ya existía.")

        # 4. Crear Usuario Administrador
        admin_user = User.query.filter_by(username="admin").first()
        if not admin_user:
            admin_user = User(
                establishment_id=establishment.id,
                username="admin",
                role="admin"
            )
            admin_user.set_password("admin123")
            db.session.add(admin_user)
            print("  ✓ Usuario Administrador ('admin' / 'admin123') creado.")
        else:
            print("  ℹ️ El usuario 'admin' ya existía.")

        # 5. Crear Usuario Común
        common_user = User.query.filter_by(username="usuario").first()
        if not common_user:
            common_user = User(
                establishment_id=establishment.id,
                username="usuario",
                role="common"
            )
            common_user.set_password("user123")
            db.session.add(common_user)
            print("  ✓ Usuario Común ('usuario' / 'user123') creado.")
        else:
            print("  ℹ️ El usuario 'usuario' ya existía.")

        # Confirmar los cambios
        db.session.commit()
        print("\n✅ Base de datos poblada con éxito.")

if __name__ == "__main__":
    seed_database()