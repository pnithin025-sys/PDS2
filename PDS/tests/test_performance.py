"""Tests for performance scoring formulas and evaluations."""
from datetime import date
from app.models import Employee, PerformanceEvaluation


def test_performance_evaluation_score_formula(app):
    """Test standard evaluation formula and rating assignments."""
    with app.app_context():
        emp = Employee.query.filter_by(employee_code='EMP999').first()

        pe = PerformanceEvaluation(
            employee_id=emp.id,
            evaluation_period='Q1 2024',
            period_start=date(2024, 1, 1),
            period_end=date(2024, 3, 31),
            tasks_assigned=20,
            tasks_completed=18,  # 90% completion -> 0.40 * 90 = 36.0
            quality_score=90.0,  # 0.30 * 90 = 27.0
            punctuality_score=90.0,  # 0.15 * 90 = 13.5
            teamwork_score=90.0,  # 0.15 * 90 = 13.5
        )
        pe.calculate_scores()
        # Overall = 36.0 + 27.0 + 13.5 + 13.5 = 90.0
        assert pe.task_completion_pct == 90.0
        assert pe.overall_score == 90.0
        assert pe.rating == 'Excellent'


def test_top_performers_view(auth_client, client):
    """Test leaderboard view."""
    auth_client.login('hr@test.com', 'Hr@123')
    resp = client.get('/performance/top-performers')
    assert resp.status_code == 200
    assert b"Organization Leaderboard" in resp.data
