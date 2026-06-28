from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from app import db
from app.models import User, Book, Loan, Fine
from functools import wraps
from datetime import date, timedelta
import csv
import io

librarian_bp = Blueprint('librarian', __name__, url_prefix='/librarian')

def librarian_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role not in ('admin', 'librarian'):
            flash('Access denied.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated

@librarian_bp.route('/dashboard')
@login_required
@librarian_required
def dashboard():
    active_loans = Loan.query.filter_by(is_returned=False).count()
    overdue_loans = Loan.query.filter(
        Loan.is_returned == False,
        Loan.due_date < date.today()
    ).count()
    return render_template('librarian/dashboard.html',
        active_loans=active_loans,
        overdue_loans=overdue_loans)

@librarian_bp.route('/loans')
@login_required
@librarian_required
def loans():
    all_loans = Loan.query.order_by(Loan.borrow_date.desc()).all()
    return render_template('librarian/loans.html', loans=all_loans, today=date.today())

@librarian_bp.route('/issue', methods=['GET', 'POST'])
@login_required
@librarian_required
def issue_book():
    books = Book.query.filter(Book.available_copies > 0).all()
    members = User.query.filter_by(role='member', is_approved=True).all()
    if request.method == 'POST':
        user_id = int(request.form.get('user_id'))
        book_id = int(request.form.get('book_id'))
        member = User.query.get_or_404(user_id)
        book = Book.query.get_or_404(book_id)
        active_count = Loan.query.filter_by(user_id=user_id, is_returned=False).count()
        if active_count >= 5:
            flash('Member already has 5 active loans. Cannot issue more.', 'danger')
            return redirect(url_for('librarian.issue_book'))
        if book.available_copies < 1:
            flash('No available copies of this book.', 'danger')
            return redirect(url_for('librarian.issue_book'))
        due = date.today() + timedelta(days=14)
        loan = Loan(user_id=user_id, book_id=book_id,
                    borrow_date=date.today(), due_date=due)
        book.available_copies -= 1
        db.session.add(loan)
        db.session.commit()
        flash(f'Book "{book.title}" issued to {member.name}. Due: {due}', 'success')
        return redirect(url_for('librarian.loans'))
    return render_template('librarian/issue_book.html', books=books, members=members)

@librarian_bp.route('/return/<int:loan_id>')
@login_required
@librarian_required
def return_book(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.is_returned:
        flash('This book has already been returned.', 'warning')
        return redirect(url_for('librarian.loans'))
    loan.is_returned = True
    loan.return_date = date.today()
    loan.book.available_copies += 1
    if date.today() > loan.due_date:
        days_overdue = (date.today() - loan.due_date).days
        fine_amount = round(days_overdue * 0.50, 2)
        fine = Fine(loan_id=loan.id, amount=fine_amount)
        db.session.add(fine)
        flash(f'Book returned. Overdue by {days_overdue} days. Fine: ¥{fine_amount}', 'warning')
    else:
        flash('Book returned successfully. No fine.', 'success')
    db.session.commit()
    return redirect(url_for('librarian.loans'))

@librarian_bp.route('/books')
@login_required
@librarian_required
def books():
    search = request.args.get('search', '')
    if search:
        books = Book.query.filter(
            (Book.title.ilike(f'%{search}%')) |
            (Book.author.ilike(f'%{search}%')) |
            (Book.isbn.ilike(f'%{search}%'))
        ).all()
    else:
        books = Book.query.all()
    return render_template('librarian/books.html', books=books, search=search)

@librarian_bp.route('/books/add', methods=['GET', 'POST'])
@login_required
@librarian_required
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        category = request.form.get('category')
        total_copies = int(request.form.get('total_copies', 1))
        if Book.query.filter_by(isbn=isbn).first():
            flash('A book with this ISBN already exists.', 'danger')
            return redirect(url_for('librarian.add_book'))
        cover_image = request.form.get('cover_image', '')
        description = request.form.get('description', '')
        book = Book(title=title, author=author, isbn=isbn,
                    category=category, cover_image=cover_image,
                    description=description,
                    total_copies=total_copies,
                    available_copies=total_copies)
        db.session.add(book)
        db.session.commit()
        flash('Book added successfully.', 'success')
        return redirect(url_for('librarian.books'))
    return render_template('librarian/add_book.html')

@librarian_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
@librarian_required
def edit_book(book_id):
    book = Book.query.get_or_404(book_id)
    if request.method == 'POST':
        book.title = request.form.get('title')
        book.author = request.form.get('author')
        book.category = request.form.get('category')
        book.cover_image = request.form.get('cover_image', '')
        book.description = request.form.get('description', '')
        new_total = int(request.form.get('total_copies', 1))
        diff = new_total - book.total_copies
        book.total_copies = new_total
        book.available_copies = max(0, book.available_copies + diff)
        db.session.commit()
        flash('Book updated successfully.', 'success')
        return redirect(url_for('librarian.books'))
    return render_template('librarian/edit_book.html', book=book)

@librarian_bp.route('/books/delete/<int:book_id>')
@login_required
@librarian_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.loans:
        flash('Cannot delete a book with loan history.', 'danger')
        return redirect(url_for('librarian.books'))
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted.', 'success')
    return redirect(url_for('librarian.books'))

@librarian_bp.route('/reports')
@login_required
@librarian_required
def reports():
    most_borrowed = db.session.query(
        Book, db.func.count(Loan.id).label('borrow_count')
    ).join(Loan).group_by(Book.id).order_by(db.text('borrow_count DESC')).limit(10).all()

    overdue_loans = Loan.query.filter(
        Loan.is_returned == False,
        Loan.due_date < date.today()
    ).all()

    today = date.today()
    daily_loans = Loan.query.filter(
        Loan.borrow_date == today
    ).all()

    return render_template('librarian/reports.html',
        most_borrowed=most_borrowed,
        overdue_loans=overdue_loans,
        daily_loans=daily_loans,
        today=today)

@librarian_bp.route('/reports/export')
@login_required
@librarian_required
def export_report():
    loans = Loan.query.order_by(Loan.borrow_date.desc()).all()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Loan ID', 'Member', 'Email', 'Book', 'ISBN',
                     'Borrow Date', 'Due Date', 'Return Date', 'Status', 'Fine'])
    for loan in loans:
        status = 'Returned' if loan.is_returned else (
            'Overdue' if loan.due_date < date.today() else 'Active')
        fine = float(loan.fine.amount) if loan.fine else 0.0
        writer.writerow([
            loan.id, loan.member.name, loan.member.email,
            loan.book.title, loan.book.isbn,
            loan.borrow_date, loan.due_date,
            loan.return_date or '', status, fine
        ])
    output.seek(0)
    response = make_response(output.getvalue())
    response.headers['Content-Disposition'] = 'attachment; filename=loans_report.csv'
    response.headers['Content-Type'] = 'text/csv'
    return response