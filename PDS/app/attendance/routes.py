"""Attendance management blueprint."""
import csv
import io
from datetime import datetime, date, time, timedelta
from flask import Blueprint, render_template, redirect, url_for, flash, request, Response, make_response
from flask_login import login_required, current_user
from app.extensions import db
from app.models import Employee, Attendance, Department, AuditLog
from app.auth.routes import hr_required

attendance_bp = Blueprint('attendance', __name__, url_prefix='/attendance')


@attendance_bp.route('/')
@login_required
def attendance_list():
    """List attendance records with filters."""
    page = request.args.get('page', 1, type=int)
    emp_filter = request.args.get('employee_id', '', type=str)
    dept_filter = request.args.get('department', '', type=str)
    date_from = request.args.get('date_from', '', type=str)
    date_to = request.args.get('date_to', '', type=str)
    status_filter = request.args.get('status', '', type=str)
    
    query = Attendance.query.join(Employee)
    
    # Employees can only see their own attendance
    if current_user.role == 'employee':
        if not current_user.employee_id:
            first_emp = Employee.query.filter_by(email=current_user.email).first() or Employee.query.first()
            if first_emp:
                current_user.employee_id = first_emp.id
                db.session.commit()
        if current_user.employee_id:
            query = query.filter(Attendance.employee_id == current_user.employee_id)
    
    if emp_filter:
        query = query.filter(Attendance.employee_id == emp_filter)
    
    if dept_filter:
        query = query.filter(Employee.department_id == dept_filter)
    
    if date_from:
        query = query.filter(Attendance.attendance_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    
    if date_to:
        query = query.filter(Attendance.attendance_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    
    if status_filter:
        query = query.filter(Attendance.status == status_filter)
    
    query = query.order_by(Attendance.attendance_date.desc(), Employee.full_name)
    records = query.paginate(page=page, per_page=20, error_out=False)
    
    employees = Employee.query.filter_by(employment_status='active').order_by(Employee.full_name).all()
    departments = Department.query.order_by(Department.name).all()
    
    return render_template('attendance/list.html', records=records,
                          employees=employees, departments=departments,
                          emp_filter=emp_filter, dept_filter=dept_filter,
                          date_from=date_from, date_to=date_to,
                          status_filter=status_filter)


@attendance_bp.route('/mark', methods=['GET', 'POST'])
@login_required
@hr_required
def mark_attendance():
    """Mark daily attendance for employees."""
    employees = Employee.query.filter_by(employment_status='active').order_by(Employee.full_name).all()
    
    if request.method == 'POST':
        att_date_str = request.form.get('attendance_date', '')
        if not att_date_str:
            flash('Date is required.', 'danger')
            return render_template('attendance/mark.html', employees=employees)
        
        att_date = datetime.strptime(att_date_str, '%Y-%m-%d').date()
        count = 0
        errors = 0
        
        for emp in employees:
            status = request.form.get(f'status_{emp.id}', '')
            if not status:
                continue
            
            check_in_str = request.form.get(f'check_in_{emp.id}', '')
            check_out_str = request.form.get(f'check_out_{emp.id}', '')
            remarks = request.form.get(f'remarks_{emp.id}', '').strip()
            
            # Check for duplicate
            existing = Attendance.query.filter_by(employee_id=emp.id, attendance_date=att_date).first()
            if existing:
                # Update existing record
                record = existing
            else:
                record = Attendance(employee_id=emp.id, attendance_date=att_date)
            
            record.status = status
            record.remarks = remarks
            
            # Parse times
            if check_in_str:
                try:
                    record.check_in = datetime.strptime(check_in_str, '%H:%M').time()
                except ValueError:
                    record.check_in = None
            else:
                record.check_in = None
            
            if check_out_str:
                try:
                    record.check_out = datetime.strptime(check_out_str, '%H:%M').time()
                except ValueError:
                    record.check_out = None
            else:
                record.check_out = None
            
            # Calculate working hours
            working_hours = 0.0
            overtime = 0.0
            if record.check_in and record.check_out:
                dt_in = datetime.combine(att_date, record.check_in)
                dt_out = datetime.combine(att_date, record.check_out)
                if dt_out > dt_in:
                    diff = (dt_out - dt_in).total_seconds() / 3600
                    working_hours = round(diff, 2)
                    standard_hours = 8.0  # configurable
                    if working_hours > standard_hours:
                        overtime = round(working_hours - standard_hours, 2)
            
            record.working_hours = working_hours
            record.overtime_hours = overtime
            
            if not existing:
                db.session.add(record)
            count += 1
        
        db.session.commit()
        flash(f'Attendance marked for {count} employees on {att_date_str}.', 'success')
        return redirect(url_for('attendance.attendance_list'))
    
    today = date.today().strftime('%Y-%m-%d')
    return render_template('attendance/mark.html', employees=employees, today=today)


@attendance_bp.route('/edit/<int:record_id>', methods=['GET', 'POST'])
@login_required
@hr_required
def edit_attendance(record_id):
    """Edit a single attendance record."""
    record = Attendance.query.get_or_404(record_id)
    
    if request.method == 'POST':
        status = request.form.get('status', 'present')
        check_in_str = request.form.get('check_in', '')
        check_out_str = request.form.get('check_out', '')
        remarks = request.form.get('remarks', '').strip()
        
        record.status = status
        record.remarks = remarks
        
        if check_in_str:
            try:
                record.check_in = datetime.strptime(check_in_str, '%H:%M').time()
            except ValueError:
                record.check_in = None
        else:
            record.check_in = None
        
        if check_out_str:
            try:
                record.check_out = datetime.strptime(check_out_str, '%H:%M').time()
            except ValueError:
                record.check_out = None
        else:
            record.check_out = None
        
        # Recalculate working hours
        working_hours = 0.0
        overtime = 0.0
        if record.check_in and record.check_out:
            dt_in = datetime.combine(record.attendance_date, record.check_in)
            dt_out = datetime.combine(record.attendance_date, record.check_out)
            if dt_out > dt_in:
                diff = (dt_out - dt_in).total_seconds() / 3600
                working_hours = round(diff, 2)
                if working_hours > 8.0:
                    overtime = round(working_hours - 8.0, 2)
        
        record.working_hours = working_hours
        record.overtime_hours = overtime
        
        log = AuditLog(user_id=current_user.id, action='edited attendance',
                      entity_type='attendance', entity_id=record.id,
                      ip_address=request.remote_addr)
        db.session.add(log)
        db.session.commit()
        
        flash('Attendance record updated.', 'success')
        return redirect(url_for('attendance.attendance_list'))
    
    return render_template('attendance/edit.html', record=record)


@attendance_bp.route('/import', methods=['GET', 'POST'])
@login_required
@hr_required
def import_attendance():
    """Import attendance from CSV file."""
    if request.method == 'POST':
        file = request.files.get('csv_file')
        if not file or not file.filename.endswith('.csv'):
            flash('Please upload a valid CSV file.', 'danger')
            return render_template('attendance/import.html')
        
        try:
            stream = io.StringIO(file.stream.read().decode('utf-8'))
            reader = csv.DictReader(stream)
            count = 0
            errors_list = []
            
            for i, row in enumerate(reader, start=2):
                try:
                    emp_code = row.get('employee_code', '').strip()
                    att_date_str = row.get('date', '').strip()
                    status = row.get('status', 'present').strip().lower()
                    check_in_str = row.get('check_in', '').strip()
                    check_out_str = row.get('check_out', '').strip()
                    remarks = row.get('remarks', '').strip()
                    
                    employee = Employee.query.filter_by(employee_code=emp_code).first()
                    if not employee:
                        errors_list.append(f'Row {i}: Employee {emp_code} not found.')
                        continue
                    
                    att_date = datetime.strptime(att_date_str, '%Y-%m-%d').date()
                    
                    # Check duplicate
                    existing = Attendance.query.filter_by(employee_id=employee.id, attendance_date=att_date).first()
                    if existing:
                        errors_list.append(f'Row {i}: Duplicate record for {emp_code} on {att_date_str}, skipping.')
                        continue
                    
                    record = Attendance(
                        employee_id=employee.id,
                        attendance_date=att_date,
                        status=status if status in ('present', 'absent', 'late', 'half_day', 'leave', 'holiday') else 'present',
                        remarks=remarks
                    )
                    
                    if check_in_str:
                        record.check_in = datetime.strptime(check_in_str, '%H:%M').time()
                    if check_out_str:
                        record.check_out = datetime.strptime(check_out_str, '%H:%M').time()
                    
                    # Calculate working hours
                    if record.check_in and record.check_out:
                        dt_in = datetime.combine(att_date, record.check_in)
                        dt_out = datetime.combine(att_date, record.check_out)
                        if dt_out > dt_in:
                            diff = (dt_out - dt_in).total_seconds() / 3600
                            record.working_hours = round(diff, 2)
                            if record.working_hours > 8.0:
                                record.overtime_hours = round(record.working_hours - 8.0, 2)
                    
                    db.session.add(record)
                    count += 1
                except Exception as e:
                    errors_list.append(f'Row {i}: {str(e)}')
            
            db.session.commit()
            
            if errors_list:
                for err in errors_list[:10]:  # show first 10 errors
                    flash(err, 'warning')
            
            flash(f'Successfully imported {count} attendance records.', 'success')
            return redirect(url_for('attendance.attendance_list'))
        
        except Exception as e:
            flash(f'Error processing CSV: {str(e)}', 'danger')
    
    return render_template('attendance/import.html')


@attendance_bp.route('/export')
@login_required
@hr_required
def export_attendance():
    """Export attendance records as CSV."""
    date_from = request.args.get('date_from', '')
    date_to = request.args.get('date_to', '')
    dept_filter = request.args.get('department', '')
    
    query = Attendance.query.join(Employee).order_by(Attendance.attendance_date.desc())
    
    if date_from:
        query = query.filter(Attendance.attendance_date >= datetime.strptime(date_from, '%Y-%m-%d').date())
    if date_to:
        query = query.filter(Attendance.attendance_date <= datetime.strptime(date_to, '%Y-%m-%d').date())
    if dept_filter:
        query = query.filter(Employee.department_id == dept_filter)
    
    records = query.all()
    
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(['Employee Code', 'Employee Name', 'Department', 'Date', 'Check In',
                     'Check Out', 'Working Hours', 'Overtime', 'Status', 'Remarks'])
    
    for r in records:
        writer.writerow([
            r.employee.employee_code, r.employee.full_name,
            r.employee.department.name, r.attendance_date.strftime('%Y-%m-%d'),
            r.check_in.strftime('%H:%M') if r.check_in else '',
            r.check_out.strftime('%H:%M') if r.check_out else '',
            r.working_hours, r.overtime_hours, r.status, r.remarks or ''
        ])
    
    response = make_response(output.getvalue())
    response.headers['Content-Type'] = 'text/csv'
    response.headers['Content-Disposition'] = f'attachment; filename=attendance_export_{date.today().strftime("%Y%m%d")}.csv'
    return response


@attendance_bp.route('/monthly')
@login_required
def monthly_view():
    """Monthly attendance calendar view."""
    year = request.args.get('year', date.today().year, type=int)
    month = request.args.get('month', date.today().month, type=int)
    emp_id = request.args.get('employee_id', type=int)
    
    # Employees can only see their own
    if current_user.role == 'employee':
        if not current_user.employee_id:
            first_emp = Employee.query.filter_by(email=current_user.email).first() or Employee.query.first()
            if first_emp:
                current_user.employee_id = first_emp.id
                db.session.commit()
        emp_id = current_user.employee_id
    
    employees = Employee.query.filter_by(employment_status='active').order_by(Employee.full_name).all()
    
    monthly_data = {}
    if emp_id:
        import calendar
        _, days_in_month = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, days_in_month)
        
        records = Attendance.query.filter(
            Attendance.employee_id == emp_id,
            Attendance.attendance_date >= start_date,
            Attendance.attendance_date <= end_date
        ).all()
        
        for r in records:
            monthly_data[r.attendance_date.day] = r
        
        employee = Employee.query.get(emp_id)
        
        # Calculate summary
        present_days = sum(1 for r in records if r.status in ('present', 'late'))
        absent_days = sum(1 for r in records if r.status == 'absent')
        late_days = sum(1 for r in records if r.status == 'late')
        half_days = sum(1 for r in records if r.status == 'half_day')
        leave_days = sum(1 for r in records if r.status == 'leave')
        holidays = sum(1 for r in records if r.status == 'holiday')
        total_working = sum(r.working_hours for r in records)
        total_overtime = sum(r.overtime_hours for r in records)
        
        # Attendance percentage: (present + late + half_day*0.5) / (working_days - holidays - leaves)
        eligible_days = days_in_month - holidays - leave_days
        if eligible_days > 0:
            att_pct = round(((present_days + half_days * 0.5) / eligible_days) * 100, 1)
        else:
            att_pct = 0
        
        summary = {
            'present': present_days, 'absent': absent_days, 'late': late_days,
            'half_day': half_days, 'leave': leave_days, 'holiday': holidays,
            'total_working_hours': round(total_working, 1),
            'total_overtime': round(total_overtime, 1),
            'attendance_pct': att_pct,
            'days_in_month': days_in_month
        }
    else:
        employee = None
        summary = None
        import calendar
        _, days_in_month = calendar.monthrange(year, month)
    
    return render_template('attendance/monthly.html', monthly_data=monthly_data,
                          employees=employees, employee=employee, year=year, month=month,
                          days_in_month=days_in_month, summary=summary, emp_id=emp_id)


@attendance_bp.route('/clock-in', methods=['POST'])
@login_required
def clock_in():
    """Real-time clock in for the logged-in employee on today's date."""
    if not current_user.employee_id:
        first_emp = Employee.query.filter_by(email=current_user.email).first() or Employee.query.first()
        if first_emp:
            current_user.employee_id = first_emp.id
            db.session.commit()

    emp_id = current_user.employee_id
    if not emp_id:
        flash('No employee record linked to your user account.', 'warning')
        return redirect(request.referrer or url_for('analytics.dashboard'))

    today = date.today()
    existing = Attendance.query.filter_by(employee_id=emp_id, attendance_date=today).first()
    now_time = datetime.now().time()
    grace_cutoff = time(9, 30)

    if existing and existing.check_in:
        flash(f'You have already clocked in today at {existing.check_in.strftime("%I:%M %p")}.', 'info')
        return redirect(request.referrer or url_for('analytics.dashboard'))

    status = 'late' if now_time > grace_cutoff else 'present'
    remark = 'Late clock-in recorded' if status == 'late' else 'On-time clock-in'

    if existing:
        existing.status = status
        existing.check_in = now_time
        existing.remarks = remark
    else:
        record = Attendance(
            employee_id=emp_id,
            attendance_date=today,
            status=status,
            check_in=now_time,
            remarks=remark
        )
        db.session.add(record)

    db.session.commit()
    flash(f'Clocked in successfully at {now_time.strftime("%I:%M %p")} ({status.capitalize()}).', 'success')
    return redirect(request.referrer or url_for('analytics.dashboard'))


@attendance_bp.route('/clock-out', methods=['POST'])
@login_required
def clock_out():
    """Real-time clock out for the logged-in employee on today's date."""
    emp_id = current_user.employee_id
    if not emp_id:
        flash('No employee record linked to your user account.', 'warning')
        return redirect(request.referrer or url_for('analytics.dashboard'))

    today = date.today()
    record = Attendance.query.filter_by(employee_id=emp_id, attendance_date=today).first()

    if not record or not record.check_in:
        flash('You have not clocked in yet today.', 'warning')
        return redirect(request.referrer or url_for('analytics.dashboard'))

    now_time = datetime.now().time()
    record.check_out = now_time

    dt_in = datetime.combine(today, record.check_in)
    dt_out = datetime.combine(today, now_time)
    if dt_out > dt_in:
        diff = (dt_out - dt_in).total_seconds() / 3600
        record.working_hours = round(diff, 2)
        if record.working_hours > 8.0:
            record.overtime_hours = round(record.working_hours - 8.0, 2)

    db.session.commit()
    flash(f'Clocked out successfully at {now_time.strftime("%I:%M %p")}. Total: {record.working_hours}h worked.', 'success')
    return redirect(request.referrer or url_for('analytics.dashboard'))

