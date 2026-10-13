"""Payroll processing blueprint."""
import io
import csv
import calendar
from datetime import datetime, date
from flask import Blueprint, render_template, redirect, url_for, flash, request, make_response, send_file
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Employee, Attendance, Payroll, Department, AuditLog
from app.auth.routes import hr_required
from app.services.payroll_service import PayrollService

payroll_bp = Blueprint('payroll', __name__, url_prefix='/payroll')


@payroll_bp.route('/')
@login_required
def payroll_list():
    """List payroll records."""
    page = request.args.get('page', 1, type=int)
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    dept_filter = request.args.get('department', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    search = request.args.get('search', '', type=str)
    
    query = Payroll.query.join(Employee)
    
    # Employees can only see their own payroll
    if current_user.role == 'employee':
        if not current_user.employee_id:
            first_emp = Employee.query.filter_by(email=current_user.email).first() or Employee.query.first()
            if first_emp:
                current_user.employee_id = first_emp.id
                db.session.commit()
        if current_user.employee_id:
            query = query.filter(Payroll.employee_id == current_user.employee_id)
    
    if month:
        query = query.filter(Payroll.pay_month == month)
    if year:
        query = query.filter(Payroll.pay_year == year)
    if dept_filter:
        query = query.filter(Employee.department_id == dept_filter)
    if status_filter:
        query = query.filter(Payroll.status == status_filter)
    if search:
        query = query.filter(
            db.or_(
                Employee.full_name.ilike(f'%{search}%'),
                Employee.employee_code.ilike(f'%{search}%')
            )
        )
    
    records = query.order_by(Employee.full_name).paginate(page=page, per_page=15, error_out=False)
    departments = Department.query.order_by(Department.name).all()
    
    return render_template('payroll/list.html', records=records,
                          departments=departments, month=month, year=year,
                          dept_filter=dept_filter, status_filter=status_filter,
                          search=search)


@payroll_bp.route('/generate', methods=['GET', 'POST'])
@login_required
@hr_required
def generate_payroll():
    """Generate monthly payroll for all active employees."""
    departments = Department.query.order_by(Department.name).all()
    
    if request.method == 'POST':
        month = request.form.get('month', type=int)
        year = request.form.get('year', type=int)
        dept_id = request.form.get('department_id', type=int)
        
        if not month or not year:
            flash('Month and year are required.', 'danger')
            return render_template('payroll/generate.html', departments=departments)
        
        service = PayrollService()
        result = service.generate_monthly_payroll(month, year, dept_id)
        
        if result['errors']:
            for err in result['errors'][:5]:
                flash(err, 'warning')
        
        if result['generated'] > 0:
            flash(f'Payroll generated for {result["generated"]} employees ({calendar.month_name[month]} {year}).', 'success')
        
        if result['skipped'] > 0:
            flash(f'{result["skipped"]} employees skipped (payroll already exists).', 'info')
        
        return redirect(url_for('payroll.payroll_list', month=month, year=year))
    
    return render_template('payroll/generate.html', departments=departments,
                          current_month=date.today().month, current_year=date.today().year)


@payroll_bp.route('/<int:payroll_id>')
@login_required
def view_payroll(payroll_id):
    """View payroll details / salary slip."""
    record = Payroll.query.get_or_404(payroll_id)
    
    # Employees can only see their own
    if current_user.role == 'employee':
        if not current_user.employee_id or current_user.employee_id != record.employee_id:
            flash('You can only view your own salary slip.', 'danger')
            return redirect(url_for('payroll.payroll_list'))
    
    return render_template('payroll/view.html', record=record)


@payroll_bp.route('/<int:payroll_id>/approve', methods=['POST'])
@login_required
@hr_required
def approve_payroll(payroll_id):
    """Approve a payroll record."""
    record = Payroll.query.get_or_404(payroll_id)
    
    if record.status != 'draft':
        flash('Only draft payroll records can be approved.', 'danger')
        return redirect(url_for('payroll.view_payroll', payroll_id=payroll_id))
    
    record.status = 'approved'
    record.approved_by = current_user.id
    record.approved_at = datetime.utcnow()
    
    log = AuditLog(user_id=current_user.id, action='approved payroll',
                  entity_type='payroll', entity_id=record.id,
                  details=f'Approved payroll for {record.employee.full_name} ({calendar.month_name[record.pay_month]} {record.pay_year})',
                  ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    
    flash(f'Payroll for {record.employee.full_name} approved.', 'success')
    return redirect(url_for('payroll.view_payroll', payroll_id=payroll_id))


@payroll_bp.route('/<int:payroll_id>/mark-paid', methods=['POST'])
@login_required
@hr_required
def mark_paid(payroll_id):
    """Mark payroll as paid."""
    record = Payroll.query.get_or_404(payroll_id)
    
    if record.status != 'approved':
        flash('Only approved payroll records can be marked as paid.', 'danger')
        return redirect(url_for('payroll.view_payroll', payroll_id=payroll_id))
    
    record.status = 'paid'
    
    log = AuditLog(user_id=current_user.id, action='marked payroll paid',
                  entity_type='payroll', entity_id=record.id,
                  details=f'Paid {record.employee.full_name} ({calendar.month_name[record.pay_month]} {record.pay_year})',
                  ip_address=request.remote_addr)
    db.session.add(log)
    db.session.commit()
    
    flash(f'Payroll for {record.employee.full_name} marked as paid.', 'success')
    return redirect(url_for('payroll.view_payroll', payroll_id=payroll_id))


@payroll_bp.route('/bulk-approve', methods=['POST'])
@login_required
@hr_required
def bulk_approve():
    """Approve all draft payroll records for a given month/year."""
    month = request.form.get('month', type=int)
    year = request.form.get('year', type=int)
    
    records = Payroll.query.filter_by(pay_month=month, pay_year=year, status='draft').all()
    count = 0
    for record in records:
        record.status = 'approved'
        record.approved_by = current_user.id
        record.approved_at = datetime.utcnow()
        count += 1
    
    if count > 0:
        log = AuditLog(user_id=current_user.id, action='bulk approved payroll',
                      entity_type='payroll', entity_id=None,
                      details=f'Bulk approved {count} records for {calendar.month_name[month]} {year}',
                      ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
    
    flash(f'Approved {count} payroll records.', 'success')
    return redirect(url_for('payroll.payroll_list', month=month, year=year))


@payroll_bp.route('/<int:payroll_id>/pdf')
@login_required
def download_salary_slip(payroll_id):
    """Download salary slip as PDF."""
    record = Payroll.query.get_or_404(payroll_id)
    
    # Employees can only download their own
    if current_user.role == 'employee':
        if not current_user.employee_id or current_user.employee_id != record.employee_id:
            flash('You can only download your own salary slip.', 'danger')
            return redirect(url_for('payroll.payroll_list'))
    
    from app.services.report_service import ReportService
    pdf_buffer = ReportService.generate_salary_slip_pdf(record)
    
    return send_file(pdf_buffer, as_attachment=True,
                    download_name=f'salary_slip_{record.employee.employee_code}_{record.pay_month}_{record.pay_year}.pdf',
                    mimetype='application/pdf')


@payroll_bp.route('/export')
@login_required
@hr_required
def export_payroll():
    """Export payroll data as CSV."""
    month = request.args.get('month', type=int)
    year = request.args.get('year', type=int)
    
    query = Payroll.query.join(Employee)
    if month:
        query = query.filter(Payroll.pay_month == month)
    if year:
        query = query.filter(Payroll.pay_year == year)
    
    records = query.order_by(Employee.full_name).all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Employee Code', 'Name', 'Department', 'Month', 'Year',
                     'Basic Salary', 'HRA', 'Allowances', 'Bonus', 'Overtime Pay',
                     'Gross Salary', 'Tax', 'PF', 'Other Deductions', 'Unpaid Leave Ded.',
                     'Total Deductions', 'Net Salary', 'Status'])
    
    for r in records:
        writer.writerow([
            r.employee.employee_code, r.employee.full_name,
            r.employee.department.name, r.pay_month, r.pay_year,
            r.basic_salary, r.hra, r.other_allowances, r.bonus, r.overtime_pay,
            r.gross_salary, r.tax_deduction, r.pf_deduction, r.other_deductions,
            r.unpaid_leave_deduction, r.total_deductions, r.net_salary, r.status
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=payroll_{month}_{year}.csv'
    return response
