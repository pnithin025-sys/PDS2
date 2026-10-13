"""Analytics service – computes KPIs and chart data from the database using Pandas and NumPy.

All values are derived from actual database records. Nothing is hard-coded.
When data is insufficient, the service returns sensible defaults and explanatory
messages so the frontend can show empty-state indicators.
"""
import calendar
from datetime import date, timedelta
import numpy as np
import pandas as pd
from app.extensions import db
from app.models import Employee, Attendance, Payroll, PerformanceEvaluation, Department


class AnalyticsService:
    """Central analytics engine backed by Pandas / NumPy."""

    # ─── Employee analytics ─────────────────────────────────────────
    @staticmethod
    def employee_summary():
        total = Employee.query.count()
        active = Employee.query.filter_by(employment_status='active').count()
        inactive = total - active

        # Department-wise headcount
        rows = (
            db.session.query(Department.name, db.func.count(Employee.id))
            .join(Employee, Employee.department_id == Department.id)
            .filter(Employee.employment_status == 'active')
            .group_by(Department.name)
            .all()
        )
        dept_headcount = {r[0]: r[1] for r in rows}

        # New hires by month (last 6 months)
        today = date.today()
        six_months_ago = today - timedelta(days=180)
        new_hires_q = (
            db.session.query(
                db.func.strftime('%Y-%m', Employee.date_of_joining).label('month'),
                db.func.count(Employee.id)
            )
            .filter(Employee.date_of_joining >= six_months_ago)
            .group_by('month')
            .order_by('month')
            .all()
        )
        new_hires = {r[0]: r[1] for r in new_hires_q}

        return {
            'total': total,
            'active': active,
            'inactive': inactive,
            'dept_headcount': dept_headcount,
            'new_hires_by_month': new_hires,
        }

    # ─── Attendance analytics ───────────────────────────────────────
    @staticmethod
    def attendance_summary(month=None, year=None):
        if month is None:
            month = date.today().month
        if year is None:
            year = date.today().year

        _, days_in_month = calendar.monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, days_in_month)

        records = Attendance.query.filter(
            Attendance.attendance_date >= start,
            Attendance.attendance_date <= end
        ).all()

        if not records:
            return {
                'avg_attendance_pct': 0,
                'present_count': 0,
                'absent_count': 0,
                'late_count': 0,
                'leave_count': 0,
                'holiday_count': 0,
                'half_day_count': 0,
                'status_breakdown': {},
                'message': 'No attendance data for this period.',
            }

        df = pd.DataFrame([{
            'employee_id': r.employee_id,
            'date': r.attendance_date,
            'status': r.status,
            'working_hours': r.working_hours,
            'overtime': r.overtime_hours,
        } for r in records])

        status_counts = df['status'].value_counts().to_dict()

        total_records = len(df)
        present_like = df[df['status'].isin(['present', 'late'])].shape[0]
        half_days = df[df['status'] == 'half_day'].shape[0]
        holidays = df[df['status'] == 'holiday'].shape[0]
        eligible = total_records - holidays
        avg_pct = round(((present_like + half_days * 0.5) / eligible * 100), 1) if eligible > 0 else 0

        # Present today
        today = date.today()
        present_today = Attendance.query.filter_by(
            attendance_date=today, status='present'
        ).count() + Attendance.query.filter_by(
            attendance_date=today, status='late'
        ).count()

        return {
            'avg_attendance_pct': avg_pct,
            'present_today': present_today,
            'present_count': status_counts.get('present', 0),
            'absent_count': status_counts.get('absent', 0),
            'late_count': status_counts.get('late', 0),
            'leave_count': status_counts.get('leave', 0),
            'holiday_count': status_counts.get('holiday', 0),
            'half_day_count': status_counts.get('half_day', 0),
            'status_breakdown': status_counts,
            'message': None,
        }

    @staticmethod
    def monthly_attendance_trend(months=6):
        """Attendance percentage trend for the last N months."""
        today = date.today()
        labels = []
        values = []

        for i in range(months - 1, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            _, dim = calendar.monthrange(y, m)
            start = date(y, m, 1)
            end = date(y, m, dim)

            records = Attendance.query.filter(
                Attendance.attendance_date >= start,
                Attendance.attendance_date <= end
            ).all()

            total = len(records)
            holidays = sum(1 for r in records if r.status == 'holiday')
            present = sum(1 for r in records if r.status in ('present', 'late'))
            half = sum(1 for r in records if r.status == 'half_day')
            eligible = total - holidays
            pct = round(((present + half * 0.5) / eligible * 100), 1) if eligible > 0 else 0

            labels.append(f'{calendar.month_abbr[m]} {y}')
            values.append(pct)

        return {'labels': labels, 'values': values}

    @staticmethod
    def dept_attendance_comparison(month=None, year=None):
        if month is None:
            month = date.today().month
        if year is None:
            year = date.today().year

        _, dim = calendar.monthrange(year, month)
        start = date(year, month, 1)
        end = date(year, month, dim)

        rows = (
            db.session.query(
                Department.name,
                Attendance.status,
                db.func.count(Attendance.id)
            )
            .join(Employee, Employee.id == Attendance.employee_id)
            .join(Department, Department.id == Employee.department_id)
            .filter(Attendance.attendance_date >= start, Attendance.attendance_date <= end)
            .group_by(Department.name, Attendance.status)
            .all()
        )

        dept_data = {}
        for dept_name, status, cnt in rows:
            if dept_name not in dept_data:
                dept_data[dept_name] = {'total': 0, 'present': 0, 'holiday': 0}
            dept_data[dept_name]['total'] += cnt
            if status in ('present', 'late'):
                dept_data[dept_name]['present'] += cnt
            elif status == 'half_day':
                dept_data[dept_name]['present'] += cnt * 0.5
            elif status == 'holiday':
                dept_data[dept_name]['holiday'] += cnt

        result = {}
        for dept, d in dept_data.items():
            eligible = d['total'] - d['holiday']
            result[dept] = round((d['present'] / eligible * 100), 1) if eligible > 0 else 0

        return result

    # ─── Payroll analytics ──────────────────────────────────────────
    @staticmethod
    def payroll_summary(month=None, year=None):
        if month is None:
            month = date.today().month
        if year is None:
            year = date.today().year

        records = Payroll.query.filter_by(pay_month=month, pay_year=year).all()
        if not records:
            # Fallback to latest available payroll period
            latest = Payroll.query.order_by(Payroll.pay_year.desc(), Payroll.pay_month.desc()).first()
            if latest:
                month, year = latest.pay_month, latest.pay_year
                records = Payroll.query.filter_by(pay_month=month, pay_year=year).all()

        if not records:
            return {
                'total_payroll': 0, 'avg_salary': 0, 'median_salary': 0,
                'min_salary': 0, 'max_salary': 0, 'count': 0,
                'message': 'No payroll data for this period.',
            }

        salaries = np.array([r.net_salary for r in records])
        return {
            'total_payroll': round(float(np.sum(salaries)), 2),
            'avg_salary': round(float(np.mean(salaries)), 2),
            'median_salary': round(float(np.median(salaries)), 2),
            'min_salary': round(float(np.min(salaries)), 2),
            'max_salary': round(float(np.max(salaries)), 2),
            'count': len(records),
            'message': None,
        }

    @staticmethod
    def salary_distribution():
        """Salary distribution across all active employees."""
        employees = Employee.query.filter_by(employment_status='active').all()
        if not employees:
            return {'labels': [], 'values': []}

        salaries = [e.basic_salary for e in employees]
        df = pd.DataFrame({'salary': salaries})

        bins = [0, 20000, 40000, 60000, 80000, 100000, 150000, float('inf')]
        labels = ['0-20K', '20K-40K', '40K-60K', '60K-80K', '80K-100K', '100K-150K', '150K+']
        df['range'] = pd.cut(df['salary'], bins=bins, labels=labels, right=False)
        counts = df['range'].value_counts().sort_index()

        return {'labels': list(counts.index.astype(str)), 'values': list(counts.values.tolist())}

    @staticmethod
    def dept_payroll_summary(month=None, year=None):
        if month is None:
            month = date.today().month
        if year is None:
            year = date.today().year

        rows = (
            db.session.query(Department.name, db.func.sum(Payroll.net_salary))
            .join(Employee, Employee.id == Payroll.employee_id)
            .join(Department, Department.id == Employee.department_id)
            .filter(Payroll.pay_month == month, Payroll.pay_year == year)
            .group_by(Department.name)
            .all()
        )
        if not rows:
            latest = Payroll.query.order_by(Payroll.pay_year.desc(), Payroll.pay_month.desc()).first()
            if latest:
                month, year = latest.pay_month, latest.pay_year
                rows = (
                    db.session.query(Department.name, db.func.sum(Payroll.net_salary))
                    .join(Employee, Employee.id == Payroll.employee_id)
                    .join(Department, Department.id == Employee.department_id)
                    .filter(Payroll.pay_month == month, Payroll.pay_year == year)
                    .group_by(Department.name)
                    .all()
                )
        return {r[0]: round(float(r[1]), 2) for r in rows}

    @staticmethod
    def monthly_payroll_trend(months=6):
        today = date.today()
        labels = []
        values = []
        for i in range(months - 1, -1, -1):
            m = today.month - i
            y = today.year
            while m <= 0:
                m += 12
                y -= 1
            total = db.session.query(db.func.sum(Payroll.net_salary)).filter_by(
                pay_month=m, pay_year=y).scalar() or 0
            labels.append(f'{calendar.month_abbr[m]} {y}')
            values.append(round(float(total), 2))
        return {'labels': labels, 'values': values}

    # ─── Performance analytics ──────────────────────────────────────
    @staticmethod
    def performance_summary():
        records = PerformanceEvaluation.query.all()
        if not records:
            return {
                'avg_score': 0, 'rating_distribution': {},
                'dept_avg': {}, 'message': 'No performance data available.',
            }

        scores = np.array([r.overall_score for r in records])
        ratings = [r.rating for r in records]
        df = pd.DataFrame([{
            'employee_id': r.employee_id,
            'score': r.overall_score,
            'rating': r.rating,
            'dept_id': r.employee.department_id if r.employee else None,
            'dept_name': r.employee.department.name if r.employee and r.employee.department else 'Unknown',
            'task_completion': r.task_completion_pct,
        } for r in records])

        rating_dist = df['rating'].value_counts().to_dict()
        dept_avg = df.groupby('dept_name')['score'].mean().round(1).to_dict()

        return {
            'avg_score': round(float(np.mean(scores)), 1),
            'rating_distribution': rating_dist,
            'dept_avg': dept_avg,
            'avg_task_completion': round(float(df['task_completion'].mean()), 1),
            'message': None,
        }

    @staticmethod
    def performance_vs_attendance():
        """Scatter data – correlation between attendance % and performance score.

        NOTE: Correlation does not establish causation. This chart is for
        exploratory analysis only and should not drive hiring/disciplinary
        decisions.
        """
        evaluations = PerformanceEvaluation.query.all()
        if len(evaluations) < 3:
            return {'data': [], 'message': 'Not enough data for correlation analysis (need ≥ 3 records).'}

        data_points = []
        for ev in evaluations:
            # Calculate attendance % for the evaluation period
            att_records = Attendance.query.filter(
                Attendance.employee_id == ev.employee_id,
                Attendance.attendance_date >= ev.period_start,
                Attendance.attendance_date <= ev.period_end
            ).all()

            total = len(att_records)
            if total == 0:
                continue
            holidays = sum(1 for a in att_records if a.status == 'holiday')
            present = sum(1 for a in att_records if a.status in ('present', 'late'))
            half = sum(1 for a in att_records if a.status == 'half_day')
            eligible = total - holidays
            att_pct = round(((present + half * 0.5) / eligible * 100), 1) if eligible > 0 else 0

            data_points.append({
                'name': ev.employee.full_name if ev.employee else 'Unknown',
                'attendance': att_pct,
                'performance': ev.overall_score,
            })

        return {'data': data_points, 'message': None}

    # ─── Dashboard KPIs ─────────────────────────────────────────────
    @staticmethod
    def dashboard_kpis():
        emp = AnalyticsService.employee_summary()
        att = AnalyticsService.attendance_summary()
        pay = AnalyticsService.payroll_summary()
        perf = AnalyticsService.performance_summary()

        return {
            'total_employees': emp['active'],
            'present_today': att.get('present_today', 0),
            'avg_attendance': att['avg_attendance_pct'],
            'monthly_payroll': pay['total_payroll'],
            'avg_performance': perf['avg_score'],
        }
