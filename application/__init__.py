import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager, current_user
from application.config import Config
from application.models import db, User, ExaminerProfile, StudentProfile, SystemSetting

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    try:
        return User.query.get(int(user_id))
    except (TypeError, ValueError):
        return None

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)

    # Register blueprints
    from application.controllers.auth import auth_bp
    from application.controllers.admin import admin_bp
    from application.controllers.examiner import examiner_bp
    from application.controllers.student import student_bp
    from application.controllers.api import api_bp
    from application.controllers.notifications import notif_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(examiner_bp, url_prefix='/examiner')
    app.register_blueprint(student_bp, url_prefix='/student')
    app.register_blueprint(api_bp, url_prefix='/api/v1')
    app.register_blueprint(notif_bp, url_prefix='/notifications')

    # Global context processors for templates
    @app.context_processor
    def inject_global_data():
        unread_count = 0
        if current_user.is_authenticated:
            unread_count = current_user.notifications.filter_by(is_read=False).count()
        return dict(
            app_name=app.config.get('APP_NAME', 'Examination Management System'),
            unread_notifications_count=unread_count
        )

    # Initialize database tables and ensure admin user exists
    with app.app_context():
        db.create_all()
        ensure_admin_user(app)

    return app


def ensure_admin_user(app):
    """
    Specification: Admin must pre-exist in the database (no Admin registration).
    Creates default admin if not existing.
    """
    admin_username = app.config.get('ADMIN_DEFAULT_USERNAME', 'admin')
    admin_email = app.config.get('ADMIN_DEFAULT_EMAIL', 'admin@examportal.edu')
    admin_password = app.config.get('ADMIN_DEFAULT_PASSWORD', 'AdminPassword@123')

    existing_admin = User.query.filter_by(username=admin_username).first()
    if not existing_admin:
        admin = User(
            username=admin_username,
            email=admin_email,
            role='admin'
        )
        admin.set_password(admin_password)
        db.session.add(admin)
        db.session.commit()

