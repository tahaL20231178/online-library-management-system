from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app import db
from app.models import User, Book, Loan, Fine
from functools import wraps
from datetime import date, timedelta

member_bp = Blueprint('member', __name__, url_prefix='/member')

def member_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if current_user.role != 'member':
            flash('Access denied.', 'danger')
            return redirect(url_for('main.index'))
        return f(*args, **kwargs)
    return decorated

@member_bp.route('/dashboard')
@login_required
@member_required
def dashboard():
    active_loans = Loan.query.filter_by(
        user_id=current_user.id, is_returned=False).count()
    total_loans = Loan.query.filter_by(user_id=current_user.id).count()
    overdue = Loan.query.filter(
        Loan.user_id == current_user.id,
        Loan.is_returned == False,
        Loan.due_date < date.today()
    ).count()
    recommended = Book.query.filter(
        Book.available_copies > 0,
        Book.rating >= 4.4
    ).order_by(Book.rating.desc()).limit(8).all()
    return render_template('member/dashboard.html',
        active_loans=active_loans,
        total_loans=total_loans,
        overdue=overdue,
        recommended=recommended)

@member_bp.route('/loans')
@login_required
@member_required
def my_loans():
    loans = Loan.query.filter_by(user_id=current_user.id)\
        .order_by(Loan.borrow_date.desc()).all()
    return render_template('member/my_loans.html',
        loans=loans, today=date.today())

@member_bp.route('/books')
@login_required
@member_required
def browse_books():
    search = request.args.get('search', '')
    selected_category = request.args.get('category', '')
    query = Book.query
    if search:
        query = query.filter(
            (Book.title.ilike(f'%{search}%')) |
            (Book.author.ilike(f'%{search}%'))
        )
    if selected_category:
        query = query.filter(Book.category == selected_category)
    books = query.all()
    top_rated = Book.query.filter(
        Book.available_copies > 0,
        Book.rating >= 4.4
    ).order_by(Book.rating.desc()).limit(6).all()
    categories = [
        'Fiction', 'Non-Fiction', 'Science Fiction', 'Fantasy', 'Mystery',
        'Thriller', 'Romance', 'Horror', 'Biography', 'Autobiography',
        'History', 'Science', 'Technology', 'Mathematics', 'Philosophy',
        'Psychology', 'Self-Help', 'Business', 'Economics', 'Politics',
        'Law', 'Medicine', 'Art', 'Music', 'Poetry', 'Drama',
        'Children', 'Young Adult', 'Travel', 'Religion', 'Adventure'
    ]
    return render_template('member/browse_books.html',
        books=books,
        categories=categories,
        search=search,
        selected_category=selected_category,
        top_rated=top_rated
        )

@member_bp.route('/borrow/<int:book_id>', methods=['POST'])
@login_required
@member_required
def borrow_book(book_id):
    book = Book.query.get_or_404(book_id)
    active_count = Loan.query.filter_by(
        user_id=current_user.id, is_returned=False).count()
    if active_count >= 5:
        flash('You already have 5 active loans. Return a book before borrowing more.', 'danger')
        return redirect(url_for('member.browse_books'))
    if book.available_copies < 1:
        flash('Sorry, no copies of this book are currently available.', 'danger')
        return redirect(url_for('member.browse_books'))
    due = date.today() + timedelta(days=14)
    loan = Loan(user_id=current_user.id, book_id=book_id,
                borrow_date=date.today(), due_date=due)
    book.available_copies -= 1
    db.session.add(loan)
    db.session.commit()
    flash(f'You have borrowed "{book.title}". Due: {due}. Fine: ¥0.50/day after due date.', 'success')
    return redirect(url_for('member.my_loans'))