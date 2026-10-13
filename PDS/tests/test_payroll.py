"""Tests for payroll engine and salary processing."""
from datetime import date
from app.models import Employee, Payroll, Attendance
from app.services.payroll_service import PayrollService


def test_payroll_service_calculation(app):
    """Test PayrollService accurately computes gross, unpaid leaves, and net take-home."""
    with app.app_context():
        emp = Employee.query.filter_by(employee_code='EMP999').first()

        # Add 2 absent days in March 2024
        att1 = Attendance(employee_id=emp.id, attendance_date=date(2024, 3, 4), status='absent')
        att2 = Attendance(employee_id=emp.id, attendance_date=date(2024, 3, 5), status='absent')
        # Add 1 present day with 2h overtime
        att3 = Attendance(employee_id=emp.id, attendance_date=date(2024, 3, 6), status='present',
                          working_hours=10.0, overtime_hours=2.0)
        from app.extensions import db
        db.session.add_all([att1, att2, att3])
        db.session.commit()

        service = PayrollService()
        result = service.generate_monthly_payroll(3, 2024)
        assert result['generated'] == 1

        record = Payroll.query.filter_by(employee_id=emp.id, pay_month=3, pay_year=2024).first()
        assert record is not None
        assert record.days_absent == 2
        assert record.basic_salary == 60000.0
        assert record.unpaid_leave_deduction > 0
        assert record.net_salary == record.gross_salary - record.total_deductions
        assert record.status == 'draft'


def test_payroll_approval(auth_client, client, app):
    """Test approving a draft payroll record."""
    auth_client.login('hr@test.com', 'Hr@123')

    with app.app_context():
        emp = Employee.query.filter_by(employee_code='EMP999').first()
        record = Payroll(
            employee_id=emp.id,
            pay_period_start=date(2024, 2, 1),
            pay_period_end=date(2024, 2, 29),
            pay_month=2,
            pay_year=2024,
            basic_salary=60000.0,
            gross_salary=85000.0,
            total_deductions=10000.0,
            net_salary=75000.0,
            working_days=29,
            days_present=29,
            status='draft'
        )
        from app.extensions import db
        db.session.add(record)
        db.session.commit()
        payroll_id = record.id

    resp = client.post(f'/payroll/{payroll_id}/approve', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        updated = Payroll.query.get(payroll_id)
        assert updated.status == 'approved'
        assert updated.approved_by is not None
