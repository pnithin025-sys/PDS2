"""Tests for attendance tracking and calculations."""
from datetime import date
from app.models import Employee, Attendance


def test_mark_attendance(auth_client, client, app):
    """Test HR marking attendance with automated working hours calculation."""
    auth_client.login('hr@test.com', 'Hr@123')

    with app.app_context():
        emp = Employee.query.filter_by(employee_code='EMP999').first()
        emp_id = emp.id

    data = {
        'attendance_date': '2024-03-10',
        f'status_{emp_id}': 'present',
        f'check_in_{emp_id}': '09:00',
        f'check_out_{emp_id}': '18:30',
        f'remarks_{emp_id}': 'Worked 9.5 hours'
    }

    resp = client.post('/attendance/mark', data=data, follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        rec = Attendance.query.filter_by(employee_id=emp_id, attendance_date=date(2024, 3, 10)).first()
        assert rec is not None
        assert rec.status == 'present'
        assert rec.working_hours == 9.5
        assert rec.overtime_hours == 1.5


def test_attendance_list_filtered(auth_client, client):
    """Test viewing attendance log table."""
    auth_client.login('hr@test.com', 'Hr@123')
    resp = client.get('/attendance/')
    assert resp.status_code == 200
    assert b"Daily Attendance Logs" in resp.data


def test_attendance_csv_export(auth_client, client):
    """Test attendance export response is CSV."""
    auth_client.login('hr@test.com', 'Hr@123')
    resp = client.get('/attendance/export')
    assert resp.status_code == 200
    assert resp.headers['Content-Type'] == 'text/csv; charset=utf-8' or 'text/csv' in resp.headers['Content-Type']
