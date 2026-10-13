"""Database models for the Employee Performance and Payroll Analytics System."""
from datetime import datetime, date
from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import UserMixin
from app.extensions import db


class User(UserMixin, db.Model):
    """User model for authentication and authorization."""
    __tablename__ = 'users'
    
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    password_hash = db.Column(db.String(256), nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    role = db.Column(db.String(20), nullable=False, default='employee')  # admin, hr_manager, employee
    is_active = db.Column(db.Boolean, default=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    employee = db.relationship('Employee', backref='user_account', uselist=False, foreign_keys=[employee_id])
    
    def set_password(self, password):
        self.password_hash = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
    
    @property
    def is_admin(self):
        return self.role == 'admin'
    
    @property
    def is_hr(self):
        return self.role in ('admin', 'hr_manager')
    
    def __repr__(self):
        return f'<User {self.email}>'


class Department(db.Model):
    """Department model."""
    __tablename__ = 'departments'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)
    description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    employees = db.relationship('Employee', backref='department', lazy='dynamic')
    
    def __repr__(self):
        return f'<Department {self.name}>'


class Employee(db.Model):
    """Employee model with all HR-related fields."""
    __tablename__ = 'employees'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_code = db.Column(db.String(20), unique=True, nullable=False, index=True)
    full_name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False, index=True)
    phone = db.Column(db.String(20), nullable=True)
    department_id = db.Column(db.Integer, db.ForeignKey('departments.id'), nullable=False)
    designation = db.Column(db.String(100), nullable=False)
    date_of_joining = db.Column(db.Date, nullable=False)
    employment_status = db.Column(db.String(20), default='active')  # active, inactive, on_leave, terminated
    basic_salary = db.Column(db.Float, nullable=False, default=0)
    hra = db.Column(db.Float, default=0)  # House Rent Allowance
    other_allowances = db.Column(db.Float, default=0)
    tax_deduction = db.Column(db.Float, default=0)
    pf_deduction = db.Column(db.Float, default=0)  # Provident Fund
    other_deductions = db.Column(db.Float, default=0)
    manager_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=True)
    work_location = db.Column(db.String(100), default='Main Office')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    manager = db.relationship('Employee', remote_side=[id], backref='subordinates')
    attendance_records = db.relationship('Attendance', backref='employee', lazy='dynamic', cascade='all, delete-orphan')
    payroll_records = db.relationship('Payroll', backref='employee', lazy='dynamic', cascade='all, delete-orphan')
    performance_records = db.relationship('PerformanceEvaluation', backref='employee', lazy='dynamic', cascade='all, delete-orphan')
    
    @property
    def gross_salary(self):
        return self.basic_salary + self.hra + self.other_allowances
    
    @property
    def total_deductions(self):
        return self.tax_deduction + self.pf_deduction + self.other_deductions
    
    @property
    def net_salary(self):
        return self.gross_salary - self.total_deductions
    
    @property
    def initials(self):
        if not self.full_name:
            return "EP"
        parts = self.full_name.strip().split()
        if len(parts) >= 2:
            return f"{parts[0][0]}{parts[-1][0]}".upper()
        return self.full_name[:2].upper()
    
    def __repr__(self):
        return f'<Employee {self.employee_code}: {self.full_name}>'


class Attendance(db.Model):
    """Attendance tracking model."""
    __tablename__ = 'attendance'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    attendance_date = db.Column(db.Date, nullable=False)
    check_in = db.Column(db.Time, nullable=True)
    check_out = db.Column(db.Time, nullable=True)
    working_hours = db.Column(db.Float, default=0)
    status = db.Column(db.String(20), nullable=False, default='present')  # present, absent, late, half_day, leave, holiday
    overtime_hours = db.Column(db.Float, default=0)
    remarks = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    __table_args__ = (
        db.UniqueConstraint('employee_id', 'attendance_date', name='uq_employee_date'),
    )
    
    def __repr__(self):
        return f'<Attendance {self.employee_id} on {self.attendance_date}>'


class Payroll(db.Model):
    """Payroll records model."""
    __tablename__ = 'payroll'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    pay_period_start = db.Column(db.Date, nullable=False)
    pay_period_end = db.Column(db.Date, nullable=False)
    pay_month = db.Column(db.Integer, nullable=False)
    pay_year = db.Column(db.Integer, nullable=False)
    basic_salary = db.Column(db.Float, default=0)
    hra = db.Column(db.Float, default=0)
    other_allowances = db.Column(db.Float, default=0)
    bonus = db.Column(db.Float, default=0)
    overtime_pay = db.Column(db.Float, default=0)
    gross_salary = db.Column(db.Float, default=0)
    tax_deduction = db.Column(db.Float, default=0)
    pf_deduction = db.Column(db.Float, default=0)
    other_deductions = db.Column(db.Float, default=0)
    unpaid_leave_deduction = db.Column(db.Float, default=0)
    total_deductions = db.Column(db.Float, default=0)
    net_salary = db.Column(db.Float, default=0)
    working_days = db.Column(db.Integer, default=0)
    days_present = db.Column(db.Integer, default=0)
    days_absent = db.Column(db.Integer, default=0)
    status = db.Column(db.String(20), default='draft')  # draft, approved, paid
    approved_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    approved_at = db.Column(db.DateTime, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    approver = db.relationship('User', foreign_keys=[approved_by])
    
    __table_args__ = (
        db.UniqueConstraint('employee_id', 'pay_month', 'pay_year', name='uq_employee_pay_period'),
    )
    
    def __repr__(self):
        return f'<Payroll {self.employee_id} for {self.pay_month}/{self.pay_year}>'


class PerformanceEvaluation(db.Model):
    """Employee performance evaluation model."""
    __tablename__ = 'performance_evaluations'
    
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey('employees.id'), nullable=False)
    evaluation_period = db.Column(db.String(50), nullable=False)  # e.g., "Q1 2024", "Jan 2024"
    period_start = db.Column(db.Date, nullable=False)
    period_end = db.Column(db.Date, nullable=False)
    tasks_assigned = db.Column(db.Integer, default=0)
    tasks_completed = db.Column(db.Integer, default=0)
    task_completion_pct = db.Column(db.Float, default=0)
    quality_score = db.Column(db.Float, default=0)  # 0-100
    punctuality_score = db.Column(db.Float, default=0)  # 0-100
    teamwork_score = db.Column(db.Float, default=0)  # 0-100
    manager_feedback = db.Column(db.Text, nullable=True)
    overall_score = db.Column(db.Float, default=0)
    rating = db.Column(db.String(30), default='Needs Improvement')
    evaluated_by = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    evaluator = db.relationship('User', foreign_keys=[evaluated_by])
    
    def calculate_scores(self):
        """Calculate task completion percentage and overall score.
        
        Formula:
            Task Completion Score = (Completed / Assigned) * 100  (0 if no tasks assigned)
            Overall = 0.40 * TaskCompletion + 0.30 * Quality + 0.15 * Punctuality + 0.15 * Teamwork
        
        Rating categories:
            Excellent: 90-100
            Good: 75-89.99
            Satisfactory: 60-74.99
            Needs Improvement: Below 60
        """
        if self.tasks_assigned > 0:
            self.task_completion_pct = (self.tasks_completed / self.tasks_assigned) * 100
        else:
            self.task_completion_pct = 0
        
        self.overall_score = round(
            0.40 * self.task_completion_pct +
            0.30 * self.quality_score +
            0.15 * self.punctuality_score +
            0.15 * self.teamwork_score, 2
        )
        
        if self.overall_score >= 90:
            self.rating = 'Excellent'
        elif self.overall_score >= 75:
            self.rating = 'Good'
        elif self.overall_score >= 60:
            self.rating = 'Satisfactory'
        else:
            self.rating = 'Needs Improvement'
    
    def __repr__(self):
        return f'<Performance {self.employee_id} - {self.evaluation_period}>'


class AuditLog(db.Model):
    """Audit logging for sensitive operations."""
    __tablename__ = 'audit_logs'
    
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=True)
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50), nullable=False)
    entity_id = db.Column(db.Integer, nullable=True)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    user = db.relationship('User', foreign_keys=[user_id])
    
    def __repr__(self):
        return f'<AuditLog {self.action} by user {self.user_id}>'
