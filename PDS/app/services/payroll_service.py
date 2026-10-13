"""Payroll calculation service.

This service handles payroll computation. Tax, provident fund, and statutory
deduction rates used here are configurable demonstration values.  They are NOT
legally accurate for any specific jurisdiction and must be verified before
real-world use.
"""
import calendar
from datetime import date
from app.extensions import db
from app.models import Employee, Attendance, Payroll


class PayrollService:
    """Reusable payroll calculation engine."""

    # --- Configurable rate constants (demonstration values) ---
    OVERTIME_RATE_PER_HOUR = 200  # currency units per OT hour
    UNPAID_LEAVE_FACTOR = 1.0     # multiplied by per-day salary

    @staticmethod
    def calculate_payroll(employee, month, year):
        """Calculate payroll for a single employee for the given month/year.

        Calculation:
            Gross Salary = Basic Salary + HRA + Other Allowances + Bonus + Overtime Pay
            Total Deductions = Tax + PF + Other Deductions + Unpaid Leave Deduction
            Net Salary = Gross Salary - Total Deductions

        Returns a dict with all salary components or None on error.
        """
        _, days_in_month = calendar.monthrange(year, month)
        start_date = date(year, month, 1)
        end_date = date(year, month, days_in_month)

        # Attendance summary
        attendance = Attendance.query.filter(
            Attendance.employee_id == employee.id,
            Attendance.attendance_date >= start_date,
            Attendance.attendance_date <= end_date
        ).all()

        present_days = sum(1 for a in attendance if a.status in ('present', 'late'))
        half_days = sum(1 for a in attendance if a.status == 'half_day')
        absent_days = sum(1 for a in attendance if a.status == 'absent')
        leave_days = sum(1 for a in attendance if a.status == 'leave')
        holidays = sum(1 for a in attendance if a.status == 'holiday')
        total_overtime = sum(a.overtime_hours for a in attendance)

        effective_present = present_days + (half_days * 0.5)
        working_days = days_in_month - holidays

        # Salary components
        basic = employee.basic_salary
        hra = employee.hra
        other_allow = employee.other_allowances

        overtime_pay = round(total_overtime * PayrollService.OVERTIME_RATE_PER_HOUR, 2)
        bonus = 0  # can be overridden

        gross = round(basic + hra + other_allow + bonus + overtime_pay, 2)

        # Deductions
        tax = employee.tax_deduction
        pf = employee.pf_deduction
        other_ded = employee.other_deductions

        # Unpaid leave deduction
        per_day_salary = basic / days_in_month if days_in_month > 0 else 0
        unpaid_leave_ded = round(absent_days * per_day_salary * PayrollService.UNPAID_LEAVE_FACTOR, 2)

        total_ded = round(tax + pf + other_ded + unpaid_leave_ded, 2)
        net = round(gross - total_ded, 2)
        if net < 0:
            net = 0

        return {
            'basic_salary': basic,
            'hra': hra,
            'other_allowances': other_allow,
            'bonus': bonus,
            'overtime_pay': overtime_pay,
            'gross_salary': gross,
            'tax_deduction': tax,
            'pf_deduction': pf,
            'other_deductions': other_ded,
            'unpaid_leave_deduction': unpaid_leave_ded,
            'total_deductions': total_ded,
            'net_salary': net,
            'working_days': working_days,
            'days_present': int(effective_present),
            'days_absent': absent_days,
            'pay_period_start': start_date,
            'pay_period_end': end_date,
        }

    def generate_monthly_payroll(self, month, year, department_id=None):
        """Generate payroll for all active employees for a month.

        Prevents duplicate generation for the same employee/pay-period.
        Returns a summary dict.
        """
        query = Employee.query.filter_by(employment_status='active')
        if department_id:
            query = query.filter_by(department_id=department_id)

        employees = query.all()
        generated = 0
        skipped = 0
        errors = []

        for emp in employees:
            # Duplicate check
            existing = Payroll.query.filter_by(
                employee_id=emp.id, pay_month=month, pay_year=year
            ).first()
            if existing:
                skipped += 1
                continue

            try:
                data = self.calculate_payroll(emp, month, year)
                if data is None:
                    errors.append(f'Calculation failed for {emp.full_name}.')
                    continue

                record = Payroll(
                    employee_id=emp.id,
                    pay_month=month,
                    pay_year=year,
                    **data
                )
                db.session.add(record)
                generated += 1
            except Exception as e:
                errors.append(f'{emp.full_name}: {str(e)}')

        if generated > 0:
            db.session.commit()

        return {'generated': generated, 'skipped': skipped, 'errors': errors}
