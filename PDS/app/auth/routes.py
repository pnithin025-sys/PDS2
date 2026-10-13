"""Authentication blueprint."""
from functools import wraps
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from app.extensions import db
from app.models import User, AuditLog

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


def admin_required(f):
    """Decorator to require admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash('Admin access required.', 'danger')
            return redirect(url_for('analytics.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


def hr_required(f):
    """Decorator to require HR manager or admin role."""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_hr:
            flash('HR Manager access required.', 'danger')
            return redirect(url_for('analytics.dashboard'))
        return f(*args, **kwargs)
    return decorated_function


@auth_bp.route('/landing')
def landing():
    """Landing page for unauthenticated users."""
    if current_user.is_authenticated:
        return redirect(url_for('analytics.dashboard'))
    return render_template('landing.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('analytics.dashboard'))
    
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        remember = request.form.get('remember', False)
        
        if not email or not password:
            flash('Please enter both email and password.', 'danger')
            return render_template('login.html')
        
        user = User.query.filter_by(email=email).first()
        
        if user and user.check_password(password):
            if not user.is_active:
                flash('Your account has been deactivated. Contact an administrator.', 'danger')
                return render_template('login.html')
            
            login_user(user, remember=bool(remember))
            
            # Audit log
            log = AuditLog(user_id=user.id, action='login', entity_type='user',
                          entity_id=user.id, ip_address=request.remote_addr)
            db.session.add(log)
            db.session.commit()
            
            flash(f'Welcome back, {user.full_name}!', 'success')
            next_page = request.args.get('next')
            return redirect(next_page or url_for('analytics.dashboard'))
        else:
            flash('Invalid email or password.', 'danger')
    
    return render_template('login.html')


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('analytics.dashboard'))
    
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        password = request.form.get('password', '')
        confirm_password = request.form.get('confirm_password', '')
        
        errors = []
        if not full_name or len(full_name) < 2:
            errors.append('Full name is required (minimum 2 characters).')
        if not email or '@' not in email:
            errors.append('A valid email address is required.')
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters.')
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if User.query.filter_by(email=email).first():
            errors.append('Email is already registered.')
        
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('register.html')
        
        matched_emp = Employee.query.filter_by(email=email).first() or Employee.query.first()
        emp_id = matched_emp.id if matched_emp else None
        user = User(full_name=full_name, email=email, role='admin', employee_id=emp_id)
        user.set_password(password)
        db.session.add(user)
        db.session.commit()
        
        flash('Registration successful! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('register.html')


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout."""
    log = AuditLog(user_id=current_user.id, action='logout', entity_type='user',
                  entity_id=current_user.id, ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.landing'))


@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    """User profile page."""
    if request.method == 'POST':
        full_name = request.form.get('full_name', '').strip()
        current_password = request.form.get('current_password', '')
        new_password = request.form.get('new_password', '')
        confirm_password = request.form.get('confirm_password', '')

        if full_name:
            current_user.full_name = full_name

        if current_password or new_password:
            if not current_user.check_password(current_password):
                flash('Current password is incorrect.', 'danger')
                return render_template('profile.html')
            if len(new_password) < 6:
                flash('New password must be at least 6 characters.', 'danger')
                return render_template('profile.html')
            if new_password != confirm_password:
                flash('New passwords do not match.', 'danger')
                return render_template('profile.html')
            current_user.set_password(new_password)
            flash('Password updated successfully.', 'success')

        db.session.commit()
        flash('Profile updated successfully.', 'success')
        return redirect(url_for('auth.profile'))

    return render_template('profile.html')


@auth_bp.route('/manage-users')
@login_required
@admin_required
def manage_users():
    """Manage users (admin only)."""
    users = User.query.order_by(User.created_at.desc()).all()
    return render_template('manage_users.html', users=users)


@auth_bp.route('/toggle-user/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def toggle_user(user_id):
    """Activate/deactivate a user."""
    user = User.query.get_or_404(user_id)
    if user.id == current_user.id:
        flash('You cannot deactivate your own account.', 'danger')
        return redirect(url_for('auth.manage_users'))
    
    user.is_active = not user.is_active
    log = AuditLog(user_id=current_user.id, action=f'{"activated" if user.is_active else "deactivated"} user',
                  entity_type='user', entity_id=user.id, ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    
    flash(f'User {user.full_name} has been {"activated" if user.is_active else "deactivated"}.', 'success')
    return redirect(url_for('auth.manage_users'))


@auth_bp.route('/change-role/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def change_role(user_id):
    """Change a user's role."""
    user = User.query.get_or_404(user_id)
    new_role = request.form.get('role', 'employee')
    
    if new_role not in ('admin', 'hr_manager', 'employee'):
        flash('Invalid role.', 'danger')
        return redirect(url_for('auth.manage_users'))
    
    if user.id == current_user.id:
        flash('You cannot change your own role.', 'danger')
        return redirect(url_for('auth.manage_users'))
    
    old_role = user.role
    user.role = new_role
    log = AuditLog(user_id=current_user.id, action=f'changed role from {old_role} to {new_role}',
                  entity_type='user', entity_id=user.id, ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    
    flash(f'Role for {user.full_name} changed to {new_role}.', 'success')
    return redirect(url_for('auth.manage_users'))
