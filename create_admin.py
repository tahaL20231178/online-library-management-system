from app import create_app, db, bcrypt
from app.models import User

app = create_app()
with app.app_context():
    hashed = bcrypt.generate_password_hash('Admin1234').decode('utf-8')
    admin = User(
        name='Admin',
        email='admin@library.com',
        password_hash=hashed,
        role='admin',
        is_approved=True
    )
    db.session.add(admin)
    db.session.commit()
    print('Admin created successfully')