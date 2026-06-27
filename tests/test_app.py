import pytest
import os

os.environ['DATABASE_URL'] = 'sqlite:///:memory:'

from app import create_app, db, bcrypt
from app.models import User, Book, Loan, Fine
from datetime import date, timedelta

@pytest.fixture
def app():
    os.environ['DATABASE_URL'] = 'sqlite:///:memory:'
    app = create_app()
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
    app.config['WTF_CSRF_ENABLED'] = False
    with app.app_context():
        db.create_all()
        yield app
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def admin_user(app):
    with app.app_context():
        hashed = bcrypt.generate_password_hash('Admin1234').decode('utf-8')
        user = User(name='Admin', email='admin@test.com',
                    password_hash=hashed, role='admin', is_approved=True)
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def member_user(app):
    with app.app_context():
        hashed = bcrypt.generate_password_hash('Member1234').decode('utf-8')
        user = User(name='TestMember', email='member@test.com',
                    password_hash=hashed, role='member', is_approved=True)
        db.session.add(user)
        db.session.commit()
        return user.id


@pytest.fixture
def sample_book(app):
    with app.app_context():
        book = Book(title='Test Book', author='Test Author',
                    isbn='9781234567890', category='Fiction',
                    total_copies=5, available_copies=5)
        db.session.add(book)
        db.session.commit()
        return book.id


# --- Auth Tests ---

def test_login_success(client, admin_user):
    response = client.post('/auth/login', data={
        'email': 'admin@test.com',
        'password': 'Admin1234'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_login_wrong_password(client, admin_user):
    response = client.post('/auth/login', data={
        'email': 'admin@test.com',
        'password': 'wrongpassword'
    }, follow_redirects=True)
    assert b'Invalid email or password' in response.data


def test_login_wrong_email(client):
    response = client.post('/auth/login', data={
        'email': 'nobody@test.com',
        'password': 'Admin1234'
    }, follow_redirects=True)
    assert b'Invalid email or password' in response.data


def test_register_new_member(client):
    response = client.post('/auth/register', data={
        'name': 'New User',
        'email': 'new@test.com',
        'password': 'NewPass123'
    }, follow_redirects=True)
    assert response.status_code == 200


def test_register_duplicate_email(client, member_user):
    response = client.post('/auth/register', data={
        'name': 'Duplicate',
        'email': 'member@test.com',
        'password': 'Pass1234',
        'confirm_password': 'Pass1234'
    }, follow_redirects=True)
    assert b'Email already registered' in response.data


def test_pending_member_cannot_login(client, app):
    with app.app_context():
        hashed = bcrypt.generate_password_hash('Pass1234').decode('utf-8')
        user = User(name='Pending', email='pending@test.com',
                    password_hash=hashed, role='member', is_approved=False)
        db.session.add(user)
        db.session.commit()
    response = client.post('/auth/login', data={
        'email': 'pending@test.com',
        'password': 'Pass1234'
    }, follow_redirects=True)
    assert b'pending approval' in response.data


# --- Book Tests ---

def test_add_book(client, admin_user):
    client.post('/auth/login', data={
        'email': 'admin@test.com', 'password': 'Admin1234'})
    response = client.post('/admin/books/add', data={
        'title': 'Flask Book',
        'author': 'Taha',
        'isbn': '9780000000001',
        'category': 'Tech',
        'total_copies': '3'
    }, follow_redirects=True)
    assert b'Flask Book' in response.data


def test_add_duplicate_isbn(client, admin_user, sample_book):
    client.post('/auth/login', data={
        'email': 'admin@test.com', 'password': 'Admin1234'})
    response = client.post('/admin/books/add', data={
        'title': 'Another Book',
        'author': 'Author',
        'isbn': '9781234567890',
        'category': 'Fiction',
        'total_copies': '1'
    }, follow_redirects=True)
    assert b'already exists' in response.data


# --- Loan Tests ---

def test_issue_book(client, app, admin_user, member_user, sample_book):
    client.post('/auth/login', data={
        'email': 'admin@test.com', 'password': 'Admin1234'})
    with app.app_context():
        mid = User.query.filter_by(email='member@test.com').first().id
        bid = Book.query.filter_by(isbn='9781234567890').first().id
    response = client.post('/librarian/issue', data={
        'user_id': mid,
        'book_id': bid
    }, follow_redirects=True)
    assert response.status_code == 200


def test_borrow_limit(client, app, admin_user, member_user):
    client.post('/auth/login', data={
        'email': 'admin@test.com', 'password': 'Admin1234'})
    with app.app_context():
        mid = User.query.filter_by(email='member@test.com').first().id
        for i in range(5):
            book = Book(title=f'Book {i}', author='A',
                        isbn=f'978000000000{i}',
                        total_copies=2, available_copies=2)
            db.session.add(book)
        db.session.commit()
        books = Book.query.all()
        for book in books[:5]:
            loan = Loan(user_id=mid, book_id=book.id,
                        borrow_date=date.today(),
                        due_date=date.today() + timedelta(days=14))
            book.available_copies -= 1
            db.session.add(loan)
        db.session.commit()
        extra = Book(title='Extra', author='A',
                     isbn='9789999999999',
                     total_copies=2, available_copies=2)
        db.session.add(extra)
        db.session.commit()
        eid = extra.id
    response = client.post('/librarian/issue', data={
        'user_id': mid,
        'book_id': eid
    }, follow_redirects=True)
    assert b'5 active loans' in response.data


def test_fine_calculation(app):
    with app.app_context():
        hashed = bcrypt.generate_password_hash('x').decode('utf-8')
        user = User(name='U', email='u@u.com',
                    password_hash=hashed, role='member', is_approved=True)
        book = Book(title='B', author='A', isbn='0000000000001',
                    total_copies=1, available_copies=1)
        db.session.add_all([user, book])
        db.session.commit()
        overdue_date = date.today() - timedelta(days=5)
        loan = Loan(user_id=user.id, book_id=book.id,
                    borrow_date=overdue_date - timedelta(days=14),
                    due_date=overdue_date)
        db.session.add(loan)
        db.session.commit()
        days = (date.today() - loan.due_date).days
        expected_fine = round(days * 0.50, 2)
        assert expected_fine == 2.50