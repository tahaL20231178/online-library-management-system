import os
os.environ['DATABASE_URL'] = 'mysql+pymysql://root:Library2024@localhost/library_db'

from app import create_app, db
from sqlalchemy import text

app = create_app()

with app.app_context():
    db.session.execute(text("UPDATE alembic_version SET version_num='4dcabe0fe5eb'"))
    db.session.commit()
    print('Version reset to 4dcabe0fe5eb')