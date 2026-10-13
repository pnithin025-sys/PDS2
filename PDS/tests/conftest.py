"""Pytest fixtures for EPPAS test suite."""
import pytest
from datetime import date
from app import create_app
from app.extensions import db
from app.models import User, Department, Employee, Attendance, Payroll, PerformanceEvaluation


@pytest.fixture
def app():
    """Create and configure a testing Flask app."""
    test_app = create_app('testing')
    test_app.config.update({
        'TESTING': True,
        'WTF_CSRF_ENABLED': False,
        'SQLALCHEMY_DATABASE_URI': 'sqlite:///:memory:',
        'SERVER_NAME': 'localhost',
    })

    with test_app.app_context():
        db.create_all()

        # Create basic department
        dept = Department(name="Engineering", description="Software & Systems")
        db.session.add(dept)
        db.session.flush()

        # Create Admin
        admin = User(full_name="Admin Test", email="admin@test.com", role="admin", is_active=True)
        admin.set_password("Admin@123")
        db.session.add(admin)

        # Create HR
        hr = User(full_name="HR Test", email="hr@test.com", role="hr_manager", is_active=True)
        hr.set_password("Hr@123")
        db.session.add(hr)

        # Create Employee
        emp_obj = Employee(
            employee_code="EMP999",
            full_name="John Doe",
            email="john@test.com",
            department_id=dept.id,
            designation="Software Engineer",
            date_of_joining=date(2023, 1, 1),
            employment_status="active",
            basic_salary=60000.0,
            hra=20000.0,
            other_allowances=5000.0,
            tax_deduction=5000.0,
            pf_deduction=4800.0,
            other_deductions=200.0
        )
        db.session.add(emp_obj)
        db.session.commit()

        # Create Employee User
        user_emp = User(full_name="John Doe", email="john@test.com", role="employee", is_active=True, employee_id=emp_obj.id)
        user_emp.set_password("Emp@123")
        db.session.add(user_emp)
        db.session.commit()

        yield test_app

        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(app):
    """A test client for the app."""
    return app.test_client()


@pytest.fixture
def auth_client(client):
    """Helper to log in with different roles."""
    class AuthHelper:
        @staticmethod
        def login(email, password):
            return client.post('/auth/login', data={'email': email, 'password': password}, follow_redirects=True)

        @staticmethod
        def logout():
            return client.get('/auth/logout', follow_redirects=True)

    return AuthHelper
