import os
os.environ['DATABASE_URL'] = 'mysql+pymysql://root:Library2024@localhost/library_db'

from app import create_app, db
from app.models import Book
import random

app = create_app()

ratings = [4.1, 4.2, 4.4, 4.5, 4.6, 4.7, 4.8, 4.9]

with app.app_context():
    books = Book.query.all()
    for book in books:
        if book.rating is None or float(book.rating) == 4.0:
            book.rating = random.choice(ratings)
    db.session.commit()
    print(f'Updated {len(books)} books with ratings')