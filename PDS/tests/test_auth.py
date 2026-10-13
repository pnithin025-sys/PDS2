"""Tests for authentication and user access control."""
from app.models import User


def test_landing_page(client):
    """Test landing page renders properly."""
    response = client.get('/auth/landing')
    assert response.status_code == 200
    assert b"Employee Performance" in response.data


def test_login_success(auth_client):
    """Test login with valid credentials."""
    resp = auth_client.login('admin@test.com', 'Admin@123')
    assert resp.status_code == 200
    assert b"Dashboard" in resp.data


def test_login_failure(auth_client):
    """Test login with invalid credentials."""
    resp = auth_client.login('admin@test.com', 'WrongPassword')
    assert resp.status_code == 200
    assert b"Invalid email or password" in resp.data


def test_logout(auth_client):
    """Test logout redirects to landing."""
    auth_client.login('admin@test.com', 'Admin@123')
    resp = auth_client.logout()
    assert resp.status_code == 200
    assert b"logged out" in resp.data or b"Employee Performance" in resp.data


def test_employee_cannot_access_hr_only_route(auth_client, client):
    """Test role-based access control: normal employee blocked from HR routes."""
    auth_client.login('john@test.com', 'Emp@123')
    resp = client.get('/employees/add')
    assert resp.status_code in (302, 403)


def test_admin_can_access_manage_users(auth_client, client):
    """Test admin access to user management."""
    auth_client.login('admin@test.com', 'Admin@123')
    resp = client.get('/auth/manage-users')
    assert resp.status_code == 200
    assert b"User Access" in resp.data
