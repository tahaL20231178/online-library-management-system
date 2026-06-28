from app import create_app, db, bcrypt
from app.models import User

app = create_app()
with app.app_context():
    hashed = bcrypt.generate_password_hash('lib123').decode('utf-8')
    librarian = User(
        name='Librarian',
        email='librarian@library.com',
        password_hash=hashed,
        role='librarian',
        is_approved=True
    )
    db.session.add(librarian)
    db.session.commit()
    print('Librarian created successfully')
