import os
import logging
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect
from flask_mail import Mail
from sqlalchemy.orm import DeclarativeBase
from werkzeug.middleware.proxy_fix import ProxyFix

# Configure logging
logging.basicConfig(level=logging.DEBUG)

class Base(DeclarativeBase):
    pass

db = SQLAlchemy(model_class=Base)
login_manager = LoginManager()
csrf = CSRFProtect()
mail = Mail()

def create_app():
    app = Flask(__name__)
    
    # Configuration
    app.secret_key = os.environ.get("SESSION_SECRET", "accounting-saas-secret-key")
    app.config["SQLALCHEMY_DATABASE_URI"] = os.environ.get("DATABASE_URL", "postgresql://localhost/accounting_saas")
    app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
    
    # Mail configuration
    app.config["MAIL_SERVER"] = os.environ.get("MAIL_SERVER", "smtp.gmail.com")
    app.config["MAIL_PORT"] = int(os.environ.get("MAIL_PORT", "587"))
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = os.environ.get("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.environ.get("MAIL_PASSWORD")
    app.config["MAIL_DEFAULT_SENDER"] = os.environ.get("MAIL_DEFAULT_SENDER")
    
    # Upload configuration
    app.config["UPLOAD_FOLDER"] = "uploads"
    app.config["MAX_CONTENT_LENGTH"] = 16 * 1024 * 1024  # 16MB max file size
    
    # Proxy fix for production
    app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    mail.init_app(app)
    
    # Login manager configuration
    login_manager.login_view = "auth.login"
    login_manager.login_message = "Please log in to access this page."
    login_manager.login_message_category = "info"
    
    @login_manager.user_loader
    def load_user(user_id):
        from models import User
        return User.query.get(int(user_id))
    
    # Register blueprints
    from blueprints.auth import auth_bp
    from blueprints.dashboard import dashboard_bp
    from blueprints.clients import clients_bp
    from blueprints.invoices import invoices_bp
    from blueprints.vat_zakat import vat_zakat_bp
    from blueprints.tasks import tasks_bp
    from blueprints.reports import reports_bp
    from blueprints.settings import settings_bp
    
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(dashboard_bp, url_prefix="/")
    app.register_blueprint(clients_bp, url_prefix="/clients")
    app.register_blueprint(invoices_bp, url_prefix="/invoices")
    app.register_blueprint(vat_zakat_bp, url_prefix="/vat-zakat")
    app.register_blueprint(tasks_bp, url_prefix="/tasks")
    app.register_blueprint(reports_bp, url_prefix="/reports")
    app.register_blueprint(settings_bp, url_prefix="/settings")
    
    # Create database tables
    with app.app_context():
        import models
        db.create_all()
        
        # Create default admin user if not exists
        from models import User, Role
        from werkzeug.security import generate_password_hash
        
        admin_role = Role.query.filter_by(name="Admin").first()
        if not admin_role:
            admin_role = Role()
            admin_role.name = "Admin"
            admin_role.description = "System Administrator"
            db.session.add(admin_role)
        
        accountant_role = Role.query.filter_by(name="Accountant").first()
        if not accountant_role:
            accountant_role = Role()
            accountant_role.name = "Accountant" 
            accountant_role.description = "Accountant"
            db.session.add(accountant_role)
            
        client_role = Role.query.filter_by(name="Client").first()
        if not client_role:
            client_role = Role()
            client_role.name = "Client"
            client_role.description = "Client"
            db.session.add(client_role)
        
        admin_user = User.query.filter_by(email="admin@example.com").first()
        if not admin_user:
            admin_user = User()
            admin_user.username = "admin"
            admin_user.email = "admin@example.com"
            admin_user.password_hash = generate_password_hash("admin123")
            admin_user.first_name = "System"
            admin_user.last_name = "Administrator"
            admin_user.role = admin_role
            admin_user.is_active = True
            db.session.add(admin_user)
        
        db.session.commit()
    
    return app

app = create_app()
