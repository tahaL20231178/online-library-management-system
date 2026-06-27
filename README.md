# Online Library Management System

A web-based library management system built with Python/Flask and MySQL.

## Features
- Role-based access control (Admin, Librarian, Member)
- Book catalog management (add, edit, delete, search)
- Member registration with admin approval workflow
- Book borrowing and returning with automatic due date (14 days)
- Fine calculation (¥0.50/day overdue)
- Reports: most borrowed books, overdue loans, daily transactions
- CSV export for loan records

## Tech Stack
- **Backend:** Python 3.11, Flask 3.0
- **Database:** MySQL 8.0 with Flask-SQLAlchemy ORM
- **Frontend:** Jinja2 templates, Bootstrap 5.3, Chart.js
- **Auth:** Flask-Login, Flask-Bcrypt
- **Testing:** PyTest, pytest-cov

## Setup Instructions

### Prerequisites
- Python 3.11
- MySQL 8.0

### Installation
```bash
git clone https://github.com/TahaPayet/online-library-management-system.git
cd online-library-management-system
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```

### Configuration
Create a `.env` file in the root directory:

SECRET_KEY=your-secret-key

DATABASE_URL=mysql+pymysql://root:YOUR_PASSWORD@localhost/library_db

MAIL_SERVER=localhost

MAIL_PORT=25

FLASK_ENV=development
### Database Setup
```bash
mysql -u root -p -e "CREATE DATABASE library_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;"
flask --app run.py db upgrade
python create_admin.py
```

### Run
```bash
python run.py
```

Visit `http://127.0.0.1:5000`

Run `python create_admin.py` to create the default admin account.

## Running Tests
```bash
pytest tests/test_app.py -v --cov=app
```

## Project Structure
## Project Structure
- `app/` — Flask application (routes, models, templates)
- `migrations/` — Database migration files
- `tests/` — Automated test suite
- `docs/` — Project diagrams
- `run.py` — Entry point
- `requirements.txt` — Dependencies