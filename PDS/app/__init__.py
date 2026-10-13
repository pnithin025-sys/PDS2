"""Flask application factory."""
import os
from flask import Flask, redirect, url_for
from flask_login import current_user
from config import config
from app.extensions import db, login_manager, csrf, migrate
from app.models import User


def create_app(config_name='default'):
    """Create and configure the Flask application."""
    app = Flask(__name__, instance_relative_config=True)
    
    # Load configuration
    if config_name in config:
        app.config.from_object(config[config_name])
    else:
        app.config.from_object(config['default'])
    
    # Ensure instance folder exists
    os.makedirs(app.instance_path, exist_ok=True)
    os.makedirs(app.config.get('UPLOAD_FOLDER', 'uploads'), exist_ok=True)
    
    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    migrate.init_app(app, db)
    
    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))
    
    # Register blueprints
    from app.auth.routes import auth_bp
    from app.employees.routes import employees_bp
    from app.attendance.routes import attendance_bp
    from app.payroll.routes import payroll_bp
    from app.performance.routes import performance_bp
    from app.analytics.routes import analytics_bp
    from app.reports.routes import reports_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(employees_bp)
    app.register_blueprint(attendance_bp)
    app.register_blueprint(payroll_bp)
    app.register_blueprint(performance_bp)
    app.register_blueprint(analytics_bp)
    app.register_blueprint(reports_bp)
    
    # Root route
    @app.route('/')
    def index():
        if current_user.is_authenticated:
            return redirect(url_for('analytics.dashboard'))
        return redirect(url_for('auth.landing'))
    
    # Error handlers
    @app.errorhandler(404)
    def not_found(e):
        from flask import render_template
        return render_template('errors/404.html'), 404
    
    @app.errorhandler(403)
    def forbidden(e):
        from flask import render_template
        return render_template('errors/403.html'), 403
    
    @app.errorhandler(500)
    def server_error(e):
        from flask import render_template
        return render_template('errors/500.html'), 500
    
    # Context processors
    @app.context_processor
    def utility_processor():
        from datetime import datetime
        return dict(now=datetime.utcnow())
    
    # Create tables on first request if needed
    with app.app_context():
        db.create_all()
    
    return app
