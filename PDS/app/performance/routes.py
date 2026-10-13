"""Performance evaluation blueprint."""
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Employee, PerformanceEvaluation, Department, AuditLog
from app.auth.routes import hr_required

performance_bp = Blueprint('performance', __name__, url_prefix='/performance')


@performance_bp.route('/')
@login_required
def performance_list():
    """List performance evaluations."""
    page = request.args.get('page', 1, type=int)
    emp_filter = request.args.get('employee_id', '', type=str)
    dept_filter = request.args.get('department', '', type=str)
    period_filter = request.args.get('period', '', type=str)
    rating_filter = request.args.get('rating', '', type=str)
    
    query = PerformanceEvaluation.query.join(Employee)
    
    # Employees can only see their own
    if current_user.role == 'employee':
        if not current_user.employee_id:
            first_emp = Employee.query.filter_by(email=current_user.email).first() or Employee.query.first()
            if first_emp:
                current_user.employee_id = first_emp.id
                db.session.commit()
        if current_user.employee_id:
            query = query.filter(PerformanceEvaluation.employee_id == current_user.employee_id)
    
    if emp_filter:
        query = query.filter(PerformanceEvaluation.employee_id == emp_filter)
    if dept_filter:
        query = query.filter(Employee.department_id == dept_filter)
    if period_filter:
        query = query.filter(PerformanceEvaluation.evaluation_period.ilike(f'%{period_filter}%'))
    if rating_filter:
        query = query.filter(PerformanceEvaluation.rating == rating_filter)
    
    records = query.order_by(PerformanceEvaluation.period_end.desc(), Employee.full_name).paginate(
        page=page, per_page=15, error_out=False)
    
    employees = Employee.query.filter_by(employment_status='active').order_by(Employee.full_name).all()
    departments = Department.query.order_by(Department.name).all()
    
    return render_template('performance/list.html', records=records,
                          employees=employees, departments=departments,
                          emp_filter=emp_filter, dept_filter=dept_filter,
                          period_filter=period_filter, rating_filter=rating_filter)


@performance_bp.route('/add', methods=['GET', 'POST'])
@login_required
@hr_required
def add_evaluation():
    """Add a new performance evaluation."""
    employees = Employee.query.filter_by(employment_status='active').order_by(Employee.full_name).all()
    
    if request.method == 'POST':
        errors = []
        employee_id = request.form.get('employee_id', type=int)
        evaluation_period = request.form.get('evaluation_period', '').strip()
        period_start = request.form.get('period_start', '')
        period_end = request.form.get('period_end', '')
        tasks_assigned = request.form.get('tasks_assigned', 0, type=int)
        tasks_completed = request.form.get('tasks_completed', 0, type=int)
        quality_score = request.form.get('quality_score', 0, type=float)
        punctuality_score = request.form.get('punctuality_score', 0, type=float)
        teamwork_score = request.form.get('teamwork_score', 0, type=float)
        manager_feedback = request.form.get('manager_feedback', '').strip()
        
        if not employee_id:
            errors.append('Employee is required.')
        if not evaluation_period:
            errors.append('Evaluation period is required.')
        if not period_start or not period_end:
            errors.append('Period start and end dates are required.')
        if tasks_assigned < 0:
            errors.append('Tasks assigned cannot be negative.')
        if tasks_completed < 0:
            errors.append('Tasks completed cannot be negative.')
        if tasks_completed > tasks_assigned and tasks_assigned > 0:
            errors.append('Tasks completed cannot exceed tasks assigned.')
        
        for score, name in [(quality_score, 'Quality'), (punctuality_score, 'Punctuality'), (teamwork_score, 'Teamwork')]:
            if score < 0 or score > 100:
                errors.append(f'{name} score must be between 0 and 100.')
        
        if errors:
            for err in errors:
                flash(err, 'danger')
            return render_template('performance/add.html', employees=employees)
        
        evaluation = PerformanceEvaluation(
            employee_id=employee_id,
            evaluation_period=evaluation_period,
            period_start=datetime.strptime(period_start, '%Y-%m-%d').date(),
            period_end=datetime.strptime(period_end, '%Y-%m-%d').date(),
            tasks_assigned=tasks_assigned,
            tasks_completed=tasks_completed,
            quality_score=quality_score,
            punctuality_score=punctuality_score,
            teamwork_score=teamwork_score,
            manager_feedback=manager_feedback,
            evaluated_by=current_user.id
        )
        evaluation.calculate_scores()
        
        db.session.add(evaluation)
        log = AuditLog(user_id=current_user.id, action='added performance evaluation',
                      entity_type='performance', entity_id=None,
                      details=f'Evaluated {Employee.query.get(employee_id).full_name} for {evaluation_period}',
                      ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        flash(f'Performance evaluation added. Overall Score: {evaluation.overall_score} ({evaluation.rating})', 'success')
        return redirect(url_for('performance.performance_list'))
    
    return render_template('performance/add.html', employees=employees)


@performance_bp.route('/<int:eval_id>')
@login_required
def view_evaluation(eval_id):
    """View performance evaluation details."""
    evaluation = PerformanceEvaluation.query.get_or_404(eval_id)
    
    if current_user.role == 'employee':
        if not current_user.employee_id or current_user.employee_id != evaluation.employee_id:
            flash('You can only view your own performance evaluations.', 'danger')
            return redirect(url_for('performance.performance_list'))
    
    return render_template('performance/view.html', evaluation=evaluation)


@performance_bp.route('/<int:eval_id>/edit', methods=['GET', 'POST'])
@login_required
@hr_required
def edit_evaluation(eval_id):
    """Edit a performance evaluation."""
    evaluation = PerformanceEvaluation.query.get_or_404(eval_id)
    employees = Employee.query.filter_by(employment_status='active').order_by(Employee.full_name).all()
    
    if request.method == 'POST':
        evaluation.evaluation_period = request.form.get('evaluation_period', '').strip()
        evaluation.period_start = datetime.strptime(request.form.get('period_start', ''), '%Y-%m-%d').date()
        evaluation.period_end = datetime.strptime(request.form.get('period_end', ''), '%Y-%m-%d').date()
        evaluation.tasks_assigned = request.form.get('tasks_assigned', 0, type=int)
        evaluation.tasks_completed = request.form.get('tasks_completed', 0, type=int)
        evaluation.quality_score = request.form.get('quality_score', 0, type=float)
        evaluation.punctuality_score = request.form.get('punctuality_score', 0, type=float)
        evaluation.teamwork_score = request.form.get('teamwork_score', 0, type=float)
        evaluation.manager_feedback = request.form.get('manager_feedback', '').strip()
        evaluation.evaluated_by = current_user.id
        
        evaluation.calculate_scores()
        
        log = AuditLog(user_id=current_user.id, action='edited performance evaluation',
                      entity_type='performance', entity_id=evaluation.id,
                      ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        flash(f'Evaluation updated. Score: {evaluation.overall_score} ({evaluation.rating})', 'success')
        return redirect(url_for('performance.view_evaluation', eval_id=evaluation.id))
    
    return render_template('performance/edit.html', evaluation=evaluation, employees=employees)


@performance_bp.route('/top-performers')
@login_required
@hr_required
def top_performers():
    """View top-performing employees."""
    dept_filter = request.args.get('department', '', type=str)
    
    query = PerformanceEvaluation.query.join(Employee).filter(Employee.employment_status == 'active')
    
    if dept_filter:
        query = query.filter(Employee.department_id == dept_filter)
    
    # Get latest evaluation per employee
    from sqlalchemy import func
    subquery = db.session.query(
        PerformanceEvaluation.employee_id,
        func.max(PerformanceEvaluation.period_end).label('latest_end')
    ).group_by(PerformanceEvaluation.employee_id).subquery()
    
    latest_evals = PerformanceEvaluation.query.join(Employee).join(
        subquery,
        db.and_(
            PerformanceEvaluation.employee_id == subquery.c.employee_id,
            PerformanceEvaluation.period_end == subquery.c.latest_end
        )
    )
    
    if dept_filter:
        latest_evals = latest_evals.filter(Employee.department_id == dept_filter)
    
    latest_evals = latest_evals.order_by(PerformanceEvaluation.overall_score.desc()).limit(20).all()
    
    departments = Department.query.order_by(Department.name).all()
    
    return render_template('performance/top_performers.html', evaluations=latest_evals,
                          departments=departments, dept_filter=dept_filter)
