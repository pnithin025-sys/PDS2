"""Reports blueprint – PDF, CSV, Excel downloads."""
import io
import csv
import calendar
from datetime import datetime, date
from flask import Blueprint, render_template, request, make_response, send_file, flash, redirect, url_for
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Employee, Attendance, Payroll, PerformanceEvaluation, Department
from app.auth.routes import hr_required
from app.services.report_service import ReportService

reports_bp = Blueprint('reports', __name__, url_prefix='/reports')


@reports_bp.route('/')
@login_required
@hr_required
def reports_index():
    """Reports hub page."""
    departments = Department.query.order_by(Department.name).all()
    return render_template('reports/index.html', departments=departments)


# ── Employee Directory ────────────────────────────────────────────
@reports_bp.route('/employees/csv')
@login_required
@hr_required
def employees_csv():
    dept_filter = request.args.get('department', '', type=str)
    query = Employee.query.join(Department)
    if dept_filter:
        query = query.filter(Employee.department_id == dept_filter)
    employees = query.order_by(Employee.full_name).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Code', 'Name', 'Email', 'Phone', 'Department', 'Designation',
                     'Joined', 'Status', 'Basic Salary', 'Location'])
    for e in employees:
        writer.writerow([e.employee_code, e.full_name, e.email, e.phone or '',
                        e.department.name, e.designation,
                        e.date_of_joining.strftime('%Y-%m-%d'),
                        e.employment_status, e.basic_salary, e.work_location or ''])

    resp = make_response(output.getvalue())
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = f'attachment; filename=employees_{date.today()}.csv'
    return resp


@reports_bp.route('/employees/pdf')
@login_required
@hr_required
def employees_pdf():
    employees = Employee.query.join(Department).order_by(Employee.full_name).all()
    pdf = ReportService.generate_employee_report_pdf(employees)
    return send_file(pdf, as_attachment=True,
                    download_name=f'employee_directory_{date.today()}.pdf',
                    mimetype='application/pdf')


@reports_bp.route('/employees/excel')
@login_required
@hr_required
def employees_excel():
    import pandas as pd
    employees = Employee.query.join(Department).order_by(Employee.full_name).all()
    data = [{
        'Code': e.employee_code, 'Name': e.full_name, 'Email': e.email,
        'Phone': e.phone or '', 'Department': e.department.name,
        'Designation': e.designation,
        'Joined': e.date_of_joining.strftime('%Y-%m-%d'),
        'Status': e.employment_status, 'Basic Salary': e.basic_salary,
        'Location': e.work_location or ''
    } for e in employees]

    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                    download_name=f'employees_{date.today()}.xlsx',
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


# ── Attendance Reports ─────────────────────────────────────────────
@reports_bp.route('/attendance/pdf')
@login_required
@hr_required
def attendance_pdf():
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    dept = request.args.get('department', '')

    query = Attendance.query.join(Employee)
    if date_from:
        query = query.filter(Attendance.attendance_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        query = query.filter(Attendance.attendance_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    if dept:
        query = query.filter(Employee.department_id == dept)

    records = query.order_by(Attendance.attendance_date.desc()).all()
    title = 'Attendance Report'
    if date_from and date_to:
        title += f' ({date_from} to {date_to})'

    pdf = ReportService.generate_attendance_report_pdf(records, title)
    return send_file(pdf, as_attachment=True,
                    download_name=f'attendance_{date.today()}.pdf',
                    mimetype='application/pdf')


# ── Payroll Reports ────────────────────────────────────────────────
@reports_bp.route('/payroll/pdf')
@login_required
@hr_required
def payroll_pdf():
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)

    records = Payroll.query.join(Employee).filter(
        Payroll.pay_month == month, Payroll.pay_year == year
    ).order_by(Employee.full_name).all()

    pdf = ReportService.generate_payroll_summary_pdf(records, month, year)
    return send_file(pdf, as_attachment=True,
                    download_name=f'payroll_{calendar.month_abbr[month]}_{year}.pdf',
                    mimetype='application/pdf')


@reports_bp.route('/payroll/excel')
@login_required
@hr_required
def payroll_excel():
    import pandas as pd
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)

    records = Payroll.query.join(Employee).filter(
        Payroll.pay_month == month, Payroll.pay_year == year
    ).order_by(Employee.full_name).all()

    data = [{
        'Code': r.employee.employee_code, 'Name': r.employee.full_name,
        'Department': r.employee.department.name,
        'Basic': r.basic_salary, 'HRA': r.hra, 'Allowances': r.other_allowances,
        'Bonus': r.bonus, 'OT Pay': r.overtime_pay, 'Gross': r.gross_salary,
        'Tax': r.tax_deduction, 'PF': r.pf_deduction,
        'Other Ded.': r.other_deductions, 'Unpaid Leave': r.unpaid_leave_deduction,
        'Total Ded.': r.total_deductions, 'Net Salary': r.net_salary, 'Status': r.status
    } for r in records]

    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                    download_name=f'payroll_{calendar.month_abbr[month]}_{year}.xlsx',
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@reports_bp.route('/payroll/csv')
@login_required
@hr_required
def payroll_csv():
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)

    records = Payroll.query.join(Employee).filter(
        Payroll.pay_month == month, Payroll.pay_year == year
    ).order_by(Employee.full_name).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Code', 'Name', 'Department', 'Basic', 'HRA', 'Allowances',
                     'Bonus', 'OT Pay', 'Gross', 'Tax', 'PF', 'Other Ded.',
                     'Unpaid Leave', 'Total Ded.', 'Net Salary', 'Status'])
    for r in records:
        writer.writerow([r.employee.employee_code, r.employee.full_name,
                         r.employee.department.name, r.basic_salary, r.hra,
                         r.other_allowances, r.bonus, r.overtime_pay, r.gross_salary,
                         r.tax_deduction, r.pf_deduction, r.other_deductions,
                         r.unpaid_leave_deduction, r.total_deductions, r.net_salary, r.status])

    resp = make_response(output.getvalue())
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = f'attachment; filename=payroll_{calendar.month_abbr[month]}_{year}.csv'
    return resp


# ── Performance Reports ────────────────────────────────────────────
@reports_bp.route('/performance/pdf')
@login_required
@hr_required
def performance_pdf():
    dept = request.args.get('department', '')
    query = PerformanceEvaluation.query.join(Employee)
    if dept:
        query = query.filter(Employee.department_id == dept)
    records = query.order_by(PerformanceEvaluation.period_end.desc()).all()

    pdf = ReportService.generate_performance_report_pdf(records)
    return send_file(pdf, as_attachment=True,
                    download_name=f'performance_{date.today()}.pdf',
                    mimetype='application/pdf')


@reports_bp.route('/performance/excel')
@login_required
@hr_required
def performance_excel():
    import pandas as pd
    records = PerformanceEvaluation.query.join(Employee).order_by(
        PerformanceEvaluation.period_end.desc()).all()

    data = [{
        'Code': r.employee.employee_code, 'Name': r.employee.full_name,
        'Department': r.employee.department.name, 'Period': r.evaluation_period,
        'Tasks Assigned': r.tasks_assigned, 'Tasks Completed': r.tasks_completed,
        'Completion %': r.task_completion_pct, 'Quality': r.quality_score,
        'Punctuality': r.punctuality_score, 'Teamwork': r.teamwork_score,
        'Overall': r.overall_score, 'Rating': r.rating
    } for r in records]

    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                    download_name=f'performance_{date.today()}.xlsx',
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')


@reports_bp.route('/performance/csv')
@login_required
@hr_required
def performance_csv():
    records = PerformanceEvaluation.query.join(Employee).order_by(
        PerformanceEvaluation.period_end.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Code', 'Name', 'Department', 'Period', 'Tasks Assigned',
                     'Tasks Completed', 'Completion %', 'Quality', 'Punctuality',
                     'Teamwork', 'Overall Score', 'Rating'])
    for r in records:
        writer.writerow([r.employee.employee_code, r.employee.full_name,
                         r.employee.department.name, r.evaluation_period,
                         r.tasks_assigned, r.tasks_completed, r.task_completion_pct,
                         r.quality_score, r.punctuality_score, r.teamwork_score,
                         r.overall_score, r.rating])

    resp = make_response(output.getvalue())
    resp.headers['Content-Type'] = 'text/csv'
    resp.headers['Content-Disposition'] = f'attachment; filename=performance_{date.today()}.csv'
    return resp


@reports_bp.route('/attendance/excel')
@login_required
@hr_required
def attendance_excel():
    import pandas as pd
    records = Attendance.query.join(Employee).order_by(Attendance.attendance_date.desc()).all()
    data = [{
        'Employee Code': r.employee.employee_code,
        'Employee Name': r.employee.full_name,
        'Department': r.employee.department.name,
        'Date': r.attendance_date.strftime('%Y-%m-%d'),
        'Status': r.status,
        'Check In': r.check_in.strftime('%H:%M') if r.check_in else '',
        'Check Out': r.check_out.strftime('%H:%M') if r.check_out else '',
        'Working Hours': r.working_hours,
        'Overtime Hours': r.overtime_hours,
        'Remarks': r.remarks or ''
    } for r in records]

    df = pd.DataFrame(data)
    buffer = io.BytesIO()
    df.to_excel(buffer, index=False, engine='openpyxl')
    buffer.seek(0)

    return send_file(buffer, as_attachment=True,
                    download_name=f'attendance_{date.today()}.xlsx',
                    mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
