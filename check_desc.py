from app import create_app
from app.models import Book

app = create_app()

with app.app_context():
    book = Book.query.filter_by(title='The Kite Runner').first()
    if book:
        print(f'Title: {book.title}')
        print(f'Description: {book.description}')
        print(f'Type: {type(book.description)}')
    else:
        print('Book not found')