from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Book, Loan, Fine
from functools import wraps
from datetime import date, timedelta

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