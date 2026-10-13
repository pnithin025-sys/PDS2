"""Tests for analytics service and JSON chart APIs."""
from app.services.analytics_service import AnalyticsService


def test_analytics_service_employee_summary(app):
    """Test AnalyticsService employee summary metrics."""
    with app.app_context():
        summary = AnalyticsService.employee_summary()
        assert summary['total'] >= 1
        assert summary['active'] >= 1
        assert 'Engineering' in summary['dept_headcount']


def test_dashboard_api_kpis(auth_client, client):
    """Test JSON KPI endpoint consumed by Chart.js dashboard."""
    auth_client.login('admin@test.com', 'Admin@123')
    resp = client.get('/dashboard/api/kpis')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'total_employees' in data
    assert 'avg_attendance' in data
    assert 'monthly_payroll' in data
    assert 'avg_performance' in data


def test_dashboard_api_charts(auth_client, client):
    """Test chart API responses."""
    auth_client.login('admin@test.com', 'Admin@123')
    resp = client.get('/dashboard/api/dept-headcount')
    assert resp.status_code == 200
    data = resp.get_json()
    assert 'labels' in data
    assert 'values' in data

    resp2 = client.get('/dashboard/api/salary-distribution')
    assert resp2.status_code == 200
    data2 = resp2.get_json()
    assert 'labels' in data2
    assert 'values' in data2
