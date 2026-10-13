"""Analytics and dashboard blueprint."""
from datetime import date
from flask import Blueprint, render_template, jsonify, request
from flask_login import login_required, current_user
from app.services.analytics_service import AnalyticsService

analytics_bp = Blueprint('analytics', __name__, url_prefix='/dashboard')


@analytics_bp.route('/')
@login_required
def dashboard():
    """Main dashboard with KPIs and charts."""
    kpis = AnalyticsService.dashboard_kpis()
    return render_template('dashboard.html', kpis=kpis)


@analytics_bp.route('/api/kpis')
@login_required
def api_kpis():
    """API: Dashboard KPIs summary."""
    kpis = AnalyticsService.dashboard_kpis()
    return jsonify(kpis)


@analytics_bp.route('/api/attendance-trend')
@login_required
def api_attendance_trend():
    """API: Monthly attendance trend for chart."""
    data = AnalyticsService.monthly_attendance_trend(months=6)
    return jsonify(data)


@analytics_bp.route('/api/salary-distribution')
@login_required
def api_salary_distribution():
    """API: Salary distribution histogram data."""
    data = AnalyticsService.salary_distribution()
    return jsonify(data)


@analytics_bp.route('/api/dept-payroll')
@login_required
def api_dept_payroll():
    """API: Department-wise payroll summary."""
    month = request.args.get('month', date.today().month, type=int)
    year = request.args.get('year', date.today().year, type=int)
    data = AnalyticsService.dept_payroll_summary(month, year)
    return jsonify({'labels': list(data.keys()), 'values': list(data.values())})


@analytics_bp.route('/api/performance-distribution')
@login_required
def api_performance_distribution():
    """API: Performance rating distribution."""
    data = AnalyticsService.performance_summary()
    return jsonify({
        'labels': list(data['rating_distribution'].keys()),
        'values': list(data['rating_distribution'].values())
    })


@analytics_bp.route('/api/attendance-status')
@login_required
def api_attendance_status():
    """API: Attendance status breakdown (doughnut)."""
    data = AnalyticsService.attendance_summary()
    breakdown = data.get('status_breakdown', {})
    return jsonify({'labels': list(breakdown.keys()), 'values': list(breakdown.values())})


@analytics_bp.route('/api/dept-headcount')
@login_required
def api_dept_headcount():
    """API: Department-wise headcount."""
    data = AnalyticsService.employee_summary()
    hc = data.get('dept_headcount', {})
    return jsonify({'labels': list(hc.keys()), 'values': list(hc.values())})


@analytics_bp.route('/api/payroll-trend')
@login_required
def api_payroll_trend():
    """API: Monthly payroll trend."""
    data = AnalyticsService.monthly_payroll_trend(months=6)
    return jsonify(data)


@analytics_bp.route('/api/performance-vs-attendance')
@login_required
def api_performance_vs_attendance():
    """API: Performance vs attendance scatter data."""
    data = AnalyticsService.performance_vs_attendance()
    return jsonify(data)


@analytics_bp.route('/analytics')
@login_required
def analytics_detail():
    """Detailed analytics page."""
    emp = AnalyticsService.employee_summary()
    att = AnalyticsService.attendance_summary()
    pay = AnalyticsService.payroll_summary()
    perf = AnalyticsService.performance_summary()
    
    return render_template('analytics/detail.html', emp=emp, att=att, pay=pay, perf=perf)
