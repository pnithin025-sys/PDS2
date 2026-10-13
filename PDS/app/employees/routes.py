"""Employee management blueprint."""
from flask import Blueprint, render_template, redirect, url_for, flash, request, jsonify
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Employee, Department, AuditLog
from app.auth.routes import hr_required

employees_bp = Blueprint('employees', __name__, url_prefix='/employees')


@employees_bp.route('/')
@login_required
@hr_required
def employee_list():
    """List all employees with search, filter, and pagination."""
    page = request.args.get('page', 1, type=int)
    search = request.args.get('search', '', type=str)
    dept_filter = request.args.get('department', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    sort_by = request.args.get('sort', 'full_name', type=str)
    
    query = Employee.query
    
    if search:
        query = query.filter(
            db.or_(
                Employee.full_name.ilike(f'%{search}%'),
                Employee.employee_code.ilike(f'%{search}%'),
                Employee.email.ilike(f'%{search}%')
            )
        )
    
    if dept_filter:
        query = query.filter(Employee.department_id == dept_filter)
    
    if status_filter:
        query = query.filter(Employee.employment_status == status_filter)
    
    # Sorting
    sort_columns = {
        'full_name': Employee.full_name,
        'employee_code': Employee.employee_code,
        'department': Employee.department_id,
        'designation': Employee.designation,
        'date_of_joining': Employee.date_of_joining,
        'salary': Employee.basic_salary,
    }
    sort_col = sort_columns.get(sort_by, Employee.full_name)
    query = query.order_by(sort_col)
    
    employees = query.paginate(page=page, per_page=15, error_out=False)
    departments = Department.query.order_by(Department.name).all()
    
    return render_template('employees/list.html', employees=employees,
                          departments=departments, search=search,
                          dept_filter=dept_filter, status_filter=status_filter,
                          sort_by=sort_by)


@employees_bp.route('/add', methods=['GET', 'POST'])
@login_required
@hr_required
def add_employee():
    """Add a new employee."""
    departments = Department.query.order_by(Department.name).all()
    managers = Employee.query.filter_by(employment_status='active').order_by(Employee.full_name).all()
    
    if request.method == 'POST':
        errors = []
        employee_code = request.form.get('employee_code', '').strip()
        full_name = request.form.get('full_name', '').strip()
        email = request.form.get('email', '').strip().lower()
        phone = request.form.get('phone', '').strip()
        department_id = request.form.get('department_id', type=int)
        designation = request.form.get('designation', '').strip()
        date_of_joining = request.form.get('date_of_joining', '')
        basic_salary = request.form.get('basic_salary', 0, type=float)
        hra = request.form.get('hra', 0, type=float)
        other_allowances = request.form.get('other_allowances', 0, type=float)
        tax_deduction = request.form.get('tax_deduction', 0, type=float)
        pf_deduction = request.form.get('pf_deduction', 0, type=float)
        other_deductions = request.form.get('other_deductions', 0, type=float)
        manager_id = request.form.get('manager_id', type=int)
        work_location = request.form.get('work_location', 'Main Office').strip()
        
        if not employee_code:
            errors.append('Employee code is required.')
        if not full_name:
            errors.append('Full name is required.')
        if not email or '@' not in email:
            errors.append('Valid email is required.')
        if not department_id:
            errors.append('Department is required.')
        if not designation:
            errors.append('Designation is required.')
        if not date_of_joining:
            errors.append('Date of joining is required.')
        if basic_salary < 0:
            errors.append('Basic salary cannot be negative.')
        
        if Employee.query.filter_by(employee_code=employee_code).first():
            errors.append('Employee code already exists.')
        if Employee.query.filter_by(email=email).first():
            errors.append('Email already exists.')
        
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('employees/add.html', departments=departments, managers=managers)
        
        from datetime import datetime
        employee = Employee(
            employee_code=employee_code,
            full_name=full_name,
            email=email,
            phone=phone,
            department_id=department_id,
            designation=designation,
            date_of_joining=datetime.strptime(date_of_joining, '%Y-%m-%d').date(),
            basic_salary=basic_salary,
            hra=hra,
            other_allowances=other_allowances,
            tax_deduction=tax_deduction,
            pf_deduction=pf_deduction,
            other_deductions=other_deductions,
            manager_id=manager_id if manager_id else None,
            work_location=work_location,
            employment_status='active'
        )
        
        db.session.add(employee)
        log = AuditLog(user_id=current_user.id, action='created employee',
                      entity_type='employee', entity_id=None,
                      details=f'Created {full_name} ({employee_code})',
                      ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        flash(f'Employee {full_name} added successfully!', 'success')
        return redirect(url_for('employees.employee_list'))
    
    return render_template('employees/add.html', departments=departments, managers=managers)


@employees_bp.route('/<int:employee_id>')
@login_required
def view_employee(employee_id):
    """View employee details."""
    employee = Employee.query.get_or_404(employee_id)
    
    # Employees can only view their own profile
    if current_user.role == 'employee':
        if not current_user.employee_id or current_user.employee_id != employee_id:
            flash('You can only view your own profile.', 'danger')
            return redirect(url_for('analytics.dashboard'))
    
    return render_template('employees/view.html', employee=employee)


@employees_bp.route('/<int:employee_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_required
def edit_employee(employee_id):
    """Edit employee information."""
    employee = Employee.query.get_or_404(employee_id)
    departments = Department.query.order_by(Department.name).all()
    managers = Employee.query.filter(Employee.id != employee_id, Employee.employment_status == 'active').order_by(Employee.full_name).all()
    
    if request.method == 'POST':
        errors = []
        employee_code = request.form.get('employee_code', '').strip()
        email = request.form.get('email', '').strip().lower()
        
        # Check uniqueness excluding current employee
        existing = Employee.query.filter(Employee.employee_code == employee_code, Employee.id != employee_id).first()
        if existing:
            errors.append('Employee code already exists.')
        
        existing_email = Employee.query.filter(Employee.email == email, Employee.id != employee_id).first()
        if existing_email:
            errors.append('Email already exists.')
        
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('employees/edit.html', employee=employee,
                                 departments=departments, managers=managers)
        
        from datetime import datetime
        employee.employee_code = employee_code
        employee.full_name = request.form.get('full_name', '').strip()
        employee.email = email
        employee.phone = request.form.get('phone', '').strip()
        employee.department_id = request.form.get('department_id', type=int)
        employee.designation = request.form.get('designation', '').strip()
        employee.date_of_joining = datetime.strptime(request.form.get('date_of_joining', ''), '%Y-%m-%d').date()
        employee.employment_status = request.form.get('employment_status', 'active')
        employee.basic_salary = request.form.get('basic_salary', 0, type=float)
        employee.hra = request.form.get('hra', 0, type=float)
        employee.other_allowances = request.form.get('other_allowances', 0, type=float)
        employee.tax_deduction = request.form.get('tax_deduction', 0, type=float)
        employee.pf_deduction = request.form.get('pf_deduction', 0, type=float)
        employee.other_deductions = request.form.get('other_deductions', 0, type=float)
        employee.manager_id = request.form.get('manager_id', type=int) or None
        employee.work_location = request.form.get('work_location', 'Main Office').strip()
        
        log = AuditLog(user_id=current_user.id, action='updated employee',
                      entity_type='employee', entity_id=employee.id,
                      details=f'Updated {employee.full_name}',
                      ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        flash(f'Employee {employee.full_name} updated successfully!', 'success')
        return redirect(url_for('employees.view_employee', employee_id=employee.id))
    
    return render_template('employees/edit.html', employee=employee,
                          departments=departments, managers=managers)


@employees_bp.route('/<int:employee_id>/deactivate', methods=['POST'])
@login_required
@hr_required
def deactivate_employee(employee_id):
    """Deactivate an employee (soft delete)."""
    employee = Employee.query.get_or_404(employee_id)
    employee.employment_status = 'inactive'
    
    log = AuditLog(user_id=current_user.id, action='deactivated employee',
                  entity_type='employee', entity_id=employee.id,
                  details=f'Deactivated {employee.full_name}',
                  ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    
    flash(f'Employee {employee.full_name} has been deactivated.', 'warning')
    return redirect(url_for('employees.employee_list'))


@employees_bp.route('/<int:employee_id>/activate', methods=['POST'])
@login_required
@hr_required
def activate_employee(employee_id):
    """Re-activate an employee."""
    employee = Employee.query.get_or_404(employee_id)
    employee.employment_status = 'active'
    
    log = AuditLog(user_id=current_user.id, action='activated employee',
                  entity_type='employee', entity_id=employee.id,
                  details=f'Activated {employee.full_name}',
                  ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    
    flash(f'Employee {employee.full_name} has been re-activated.', 'success')
    return redirect(url_for('employees.employee_list'))


@employees_bp.route('/departments')
@login_required
@hr_required
def department_list():
    """List and manage departments."""
    departments = Department.query.order_by(Department.name).all()
    dept_stats = []
    for dept in departments:
        active_count = Employee.query.filter_by(department_id=dept.id, employment_status='active').count()
        total_count = Employee.query.filter_by(department_id=dept.id).count()
        dept_stats.append({'department': dept, 'active': active_count, 'total': total_count})
    return render_template('employees/departments.html', dept_stats=dept_stats)


@employees_bp.route('/departments/add', methods=['POST'])
@login_required
@hr_required
def add_department():
    """Add a new department."""
    name = request.form.get('name', '').strip()
    description = request.form.get('description', '').strip()
    
    if not name:
        flash('Department name is required.', 'danger')
        return redirect(url_for('employees.department_list'))
    
    if Department.query.filter_by(name=name).first():
        flash('Department already exists.', 'danger')
        return redirect(url_for('employees.department_list'))
    
    dept = Department(name=name, description=description)
    db.session.add(dept)
    db.session.commit()
    
    flash(f'Department "{name}" created successfully!', 'success')
    return redirect(url_for('employees.department_list'))
