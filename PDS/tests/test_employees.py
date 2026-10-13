"""Tests for employee lifecycle and management."""
from app.models import Employee, Department


def test_employee_list(auth_client, client):
    """Test HR manager can view employee directory."""
    auth_client.login('hr@test.com', 'Hr@123')
    resp = client.get('/employees/')
    assert resp.status_code == 200
    assert b"John Doe" in resp.data
    assert b"EMP999" in resp.data


def test_add_employee(auth_client, client, app):
    """Test creating a new employee with valid data."""
    auth_client.login('hr@test.com', 'Hr@123')
    with app.app_context():
        dept = Department.query.first()
        dept_id = dept.id

    data = {
        'employee_code': 'EMP101',
        'full_name': 'Sarah Connor',
        'email': 'sarah@test.com',
        'phone': '+91 9999888877',
        'department_id': dept_id,
        'designation': 'QA Analyst',
        'date_of_joining': '2023-05-15',
        'basic_salary': '50000',
        'hra': '15000',
        'other_allowances': '3000',
        'tax_deduction': '3000',
        'pf_deduction': '4000',
        'other_deductions': '0',
        'work_location': 'Main Office'
    }

    resp = client.post('/employees/add', data=data, follow_redirects=True)
    assert resp.status_code == 200
    assert b"Sarah Connor" in resp.data

    with app.app_context():
        emp = Employee.query.filter_by(employee_code='EMP101').first()
        assert emp is not None
        assert emp.full_name == 'Sarah Connor'
        assert emp.gross_salary == 68000.0
        assert emp.net_salary == 61000.0


def test_deactivate_activate_employee(auth_client, client, app):
    """Test soft delete and re-activation."""
    auth_client.login('hr@test.com', 'Hr@123')
    with app.app_context():
        emp = Employee.query.filter_by(employee_code='EMP999').first()
        emp_id = emp.id

    # Deactivate
    resp = client.post(f'/employees/{emp_id}/deactivate', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        emp = Employee.query.get(emp_id)
        assert emp.employment_status == 'inactive'

    # Activate
    resp = client.post(f'/employees/{emp_id}/activate', follow_redirects=True)
    assert resp.status_code == 200

    with app.app_context():
        emp = Employee.query.get(emp_id)
        assert emp.employment_status == 'active'
