from flask import Flask, request, redirect, url_for, make_response
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_bcrypt import Bcrypt
from flask_mail import Mail
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
from app.translations import zh, en

load_dotenv()

db = SQLAlchemy()
login_manager = LoginManager()
bcrypt = Bcrypt()
mail = Mail()
migrate = Migrate()

def create_app():
    app = Flask(__name__)
    app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-key')
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['MAIL_SERVER'] = os.getenv('MAIL_SERVER', 'localhost')
    app.config['MAIL_PORT'] = int(os.getenv('MAIL_PORT', 25))
    app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024

    db.init_app(app)
    login_manager.init_app(app)
    bcrypt.init_app(app)
    mail.init_app(app)
    migrate.init_app(app, db)

    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'warning'

    from app.routes.auth import auth_bp
    from app.routes.admin import admin_bp
    from app.routes.librarian import librarian_bp
    from app.routes.member import member_bp
    from app.routes.main import main_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(librarian_bp)
    app.register_blueprint(member_bp)
    app.register_blueprint(main_bp)

    @app.context_processor
    def inject_translations():
        def _(text):
            lang = request.cookies.get('lang', 'en')
            if lang == 'zh':
                return zh.get(text, text)
            return text
        return dict(_=_)

    @app.route('/lang/<code>')
    def set_lang(code):
        resp = make_response(redirect(request.referrer or url_for('main.index')))
        if code in ('en', 'zh'):
            resp.set_cookie('lang', code, max_age=365*24*3600)
        return resp

    return app
