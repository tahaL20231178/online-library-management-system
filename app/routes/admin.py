from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response
from flask_login import login_required, current_user
from app import db
from app.models import User, Book, Loan, Fine
from functools import wraps
from datetime import date, timedelta
import csv
import io

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'admin':
            flash('Access denied.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_books = Book.query.count()
    total_members = User.query.filter_by(role='member').count()
    active_loans = Loan.query.filter_by(is_returned=False).count()
    pending_approvals = User.query.filter_by(role='member', is_approved=False).count()
    return render_template('admin/dashboard.html',
        total_books=total_books,
        total_members=total_members,
        active_loans=active_loans,
        pending_approvals=pending_approvals)

@admin_bp.route('/members')
@login_required
@admin_required
def members():
    members = User.query.filter_by(role='member').all()
    return render_template('admin/members.html', members=members)

@admin_bp.route('/members/approve/<int:user_id>')
@login_required
@admin_required
def approve_member(user_id):
    user = User.query.get_or_404(user_id)
    user.is_approved = True
    db.session.commit()
    flash(f'{user.name} has been approved.', 'success')
    return redirect(url_for('admin.members'))

@admin_bp.route('/members/reject/<int:user_id>')
@login_required
@admin_required
def reject_member(user_id):
    user = User.query.get_or_404(user_id)
    db.session.delete(user)
    db.session.commit()
    flash('Member registration rejected and removed.', 'warning')
    return redirect(url_for('admin.members'))

@admin_bp.route('/books')
@login_required
@admin_required
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
    return render_template('admin/books.html', books=books, search=search)

@admin_bp.route('/books/add', methods=['GET', 'POST'])
@login_required
@admin_required
def add_book():
    if request.method == 'POST':
        title = request.form.get('title')
        author = request.form.get('author')
        isbn = request.form.get('isbn')
        category = request.form.get('category')
        total_copies = int(request.form.get('total_copies', 1))
        if Book.query.filter_by(isbn=isbn).first():
            flash('A book with this ISBN already exists.', 'danger')
            return redirect(url_for('admin.add_book'))
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
        return redirect(url_for('admin.books'))
    return render_template('admin/add_book.html')

@admin_bp.route('/books/edit/<int:book_id>', methods=['GET', 'POST'])
@login_required
@admin_required
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
        return redirect(url_for('admin.books'))
    return render_template('admin/edit_book.html', book=book)

@admin_bp.route('/books/delete/<int:book_id>')
@login_required
@admin_required
def delete_book(book_id):
    book = Book.query.get_or_404(book_id)
    if book.loans:
        flash('Cannot delete a book with loan history.', 'danger')
        return redirect(url_for('admin.books'))
    db.session.delete(book)
    db.session.commit()
    flash('Book deleted.', 'success')
    return redirect(url_for('admin.books'))

@admin_bp.route('/reports')
@login_required
@admin_required
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

    return render_template('admin/reports.html',
        most_borrowed=most_borrowed,
        overdue_loans=overdue_loans,
        daily_loans=daily_loans,
        today=today)

@admin_bp.route('/reports/export')
@login_required
@admin_required
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

@admin_bp.route('/loans')
@login_required
@admin_required
def loans():
    all_loans = Loan.query.order_by(Loan.borrow_date.desc()).all()
    return render_template('admin/loans.html', loans=all_loans, today=date.today())

@admin_bp.route('/loans/return/<int:loan_id>')
@login_required
@admin_required
def confirm_return(loan_id):
    loan = Loan.query.get_or_404(loan_id)
    if loan.is_returned:
        flash('This book has already been returned.', 'warning')
        return redirect(url_for('admin.loans'))
    loan.is_returned = True
    loan.return_date = date.today()
    loan.book.available_copies += 1
    if date.today() > loan.due_date:
        days_overdue = (date.today() - loan.due_date).days
        fine_amount = round(days_overdue * 0.50, 2)
        fine = Fine(loan_id=loan.id, amount=fine_amount)
        db.session.add(fine)
        flash(f'Return confirmed. Overdue by {days_overdue} days. Fine: ¥{fine_amount}', 'warning')
    else:
        flash('Return confirmed successfully. No fine.', 'success')
    db.session.commit()
    return redirect(url_for('admin.loans'))