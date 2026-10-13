"""Realistic database seeding script for EPPAS.

Populates departments, 50+ diverse employees, 3 user roles, 4 months of attendance
records, multi-month payroll runs, and quarterly performance evaluations.
"""
import random
from datetime import date, datetime, timedelta, time
from app import create_app
from app.extensions import db
from app.models import User, Department, Employee, Attendance, Payroll, PerformanceEvaluation, AuditLog

app = create_app('development')

DEPARTMENTS_DATA = [
    {"name": "Engineering", "description": "Software architecture, platform development, and cloud DevOps."},
    {"name": "Data Science & AI", "description": "Machine learning, statistical modeling, and predictive analytics."},
    {"name": "Product & Design", "description": "Product strategy, UX/UI design, and user research."},
    {"name": "Human Resources", "description": "Talent acquisition, employee relations, and workforce planning."},
    {"name": "Finance & Accounting", "description": "Financial reporting, payroll administration, and budgeting."},
    {"name": "Sales & Business Dev", "description": "Enterprise sales, client partnerships, and revenue operations."},
    {"name": "Customer Success", "description": "Client onboarding, product support, and relationship management."}
]

DESIGNATIONS = {
    "Engineering": ["Senior Software Engineer", "Full Stack Developer", "Backend Engineer", "Frontend Developer", "DevOps Engineer", "QA Automation Lead"],
    "Data Science & AI": ["Lead Data Scientist", "Senior ML Engineer", "Data Analyst", "Analytics Engineer", "BI Specialist"],
    "Product & Design": ["Product Manager", "Lead Product Designer", "UI/UX Designer", "Technical Writer"],
    "Human Resources": ["HR Business Partner", "Talent Acquisition Lead", "HR Operations Specialist"],
    "Finance & Accounting": ["Finance Manager", "Senior Financial Analyst", "Payroll Accountant"],
    "Sales & Business Dev": ["Enterprise Account Executive", "Sales Development Rep", "Partnership Manager"],
    "Customer Success": ["Customer Success Manager", "Technical Support Specialist", "Client Onboarding Lead"]
}

FIRST_NAMES = [
    "Aarav", "Aditi", "Rohan", "Pooja", "Vikram", "Sneha", "Karan", "Ananya", "Rahul", "Priya",
    "Siddharth", "Meera", "Arjun", "Divya", "Aditya", "Neha", "Varun", "Tanvi", "Gaurav", "Isha",
    "Rishi", "Kavya", "Manish", "Shreya", "Naveen", "Swati", "Abhishek", "Rhea", "Harish", "Nikita",
    "Deepak", "Akansha", "Kunal", "Bhavna", "Pranav", "Simran", "Sanjay", "Anjali", "Alok", "Kritika",
    "Mayank", "Pallavi", "Tarun", "Payal", "Ajay", "Preeti", "Sunil", "Ritu", "Mohit", "Deepika",
    "Vikas", "Monika"
]

LAST_NAMES = [
    "Sharma", "Verma", "Patel", "Reddy", "Nair", "Iyer", "Mehta", "Gupta", "Deshmukh", "Chopra",
    "Kulkarni", "Joshi", "Bhat", "Rao", "Menon", "Kapoor", "Bose", "Sengupta", "Malhotra", "Saxena"
]

def seed_database():
    with app.app_context():
        print("Cleaning existing database tables...")
        db.drop_all()
        db.create_all()

        print("1. Creating Departments...")
        departments = {}
        for d_data in DEPARTMENTS_DATA:
            dept = Department(name=d_data["name"], description=d_data["description"])
            db.session.add(dept)
            departments[d_data["name"]] = dept
        db.session.commit()

        print("2. Creating Core System Users (Admin, HR)...")
        admin_user = User(
            full_name="System Administrator",
            email="admin@eppas.com",
            role="admin",
            is_active=True
        )
        admin_user.set_password("Admin@123")
        db.session.add(admin_user)

        hr_user = User(
            full_name="Pooja Sharma (HR Lead)",
            email="hr@eppas.com",
            role="hr_manager",
            is_active=True
        )
        hr_user.set_password("Hr@123")
        db.session.add(hr_user)
        db.session.commit()

        print("3. Creating 50+ Diverse Employees...")
        employees = []
        random.seed(42)  # Deterministic realistic distribution

        dept_keys = list(departments.keys())
        emp_idx = 1

        for dept_name in dept_keys:
            dept_obj = departments[dept_name]
            # Create a Department Lead first
            lead_first = FIRST_NAMES[(emp_idx - 1) % len(FIRST_NAMES)]
            lead_last = LAST_NAMES[(emp_idx - 1) % len(LAST_NAMES)]
            lead_name = f"{lead_first} {lead_last}"
            lead_email = f"{lead_first.lower()}.{lead_last.lower()}@eppas.com"
            lead_code = f"EMP{emp_idx:03d}"

            lead_sal = random.choice([120000.0, 135000.0, 150000.0, 160000.0])
            hra = round(lead_sal * 0.40, 2)
            allowances = round(lead_sal * 0.15, 2)
            tax = round(lead_sal * 0.12, 2)
            pf = round(lead_sal * 0.08, 2)

            join_year = random.choice([2021, 2022])
            join_month = random.randint(1, 12)
            join_day = random.randint(1, 28)

            dept_lead = Employee(
                employee_code=lead_code,
                full_name=lead_name,
                email=lead_email,
                phone=f"+91 98{random.randint(10000000, 99999999)}",
                department_id=dept_obj.id,
                designation=f"Head of {dept_name}",
                date_of_joining=date(join_year, join_month, join_day),
                employment_status="active",
                basic_salary=lead_sal,
                hra=hra,
                other_allowances=allowances,
                tax_deduction=tax,
                pf_deduction=pf,
                other_deductions=1000.0,
                work_location="Headquarters (Bangalore)"
            )
            db.session.add(dept_lead)
            db.session.commit()
            employees.append(dept_lead)
            emp_idx += 1

            # Create team members under this dept lead
            num_members = random.randint(6, 8)
            available_titles = DESIGNATIONS.get(dept_name, ["Specialist"])

            for _ in range(num_members):
                first = FIRST_NAMES[(emp_idx - 1) % len(FIRST_NAMES)]
                last = LAST_NAMES[(emp_idx * 3) % len(LAST_NAMES)]
                name = f"{first} {last}"
                email = f"{first.lower()}.{last.lower()}{emp_idx}@eppas.com"
                code = f"EMP{emp_idx:03d}"

                base_sal = round(random.uniform(40000, 105000), -2)
                e_hra = round(base_sal * 0.35, 2)
                e_allow = round(base_sal * 0.10, 2)
                e_tax = round(base_sal * 0.10, 2)
                e_pf = round(base_sal * 0.08, 2)

                j_year = random.choice([2022, 2023, 2024])
                j_month = random.randint(1, 12) if j_year < 2024 else random.randint(1, 6)
                j_day = random.randint(1, 28)

                emp = Employee(
                    employee_code=code,
                    full_name=name,
                    email=email,
                    phone=f"+91 98{random.randint(10000000, 99999999)}",
                    department_id=dept_obj.id,
                    designation=random.choice(available_titles),
                    date_of_joining=date(j_year, j_month, j_day),
                    employment_status="active" if emp_idx != 48 else "inactive",
                    basic_salary=base_sal,
                    hra=e_hra,
                    other_allowances=e_allow,
                    tax_deduction=e_tax,
                    pf_deduction=e_pf,
                    other_deductions=500.0,
                    manager_id=dept_lead.id,
                    work_location=random.choice(["Headquarters (Bangalore)", "Tech Park Hub (Hyderabad)", "Remote - India"])
                )
                db.session.add(emp)
                employees.append(emp)
                emp_idx += 1

        db.session.commit()
        print(f"Created {len(employees)} active/inactive employees across {len(departments)} departments.")

        # Create user accounts for employees
        emp_user = User(
            full_name=employees[0].full_name,
            email="employee@eppas.com",
            role="employee",
            is_active=True,
            employee_id=employees[0].id
        )
        emp_user.set_password("Employee@123")
        db.session.add(emp_user)

        # Link HR Lead employee account
        hr_emp = next((e for e in employees if e.department.name == "Human Resources"), None)
        if hr_emp:
            hr_user.employee_id = hr_emp.id

        db.session.commit()

        print("4. Generating Attendance Logs (Last 90 Days)...")
        # Generate attendance over recent 90 days for all employees
        today = date.today()
        start_date = today - timedelta(days=90)
        curr = start_date

        statuses_weights = ["present"] * 82 + ["late"] * 8 + ["half_day"] * 3 + ["leave"] * 4 + ["absent"] * 3

        while curr <= today:
            # Skip Sundays
            if curr.weekday() == 6:
                curr += timedelta(days=1)
                continue

            # Second and Fourth Saturday holiday
            is_saturday = curr.weekday() == 5
            day_of_month = curr.day
            if is_saturday and ((day_of_month <= 7) or (15 <= day_of_month <= 21)):
                for emp in employees:
                    att = Attendance(
                        employee_id=emp.id,
                        attendance_date=curr,
                        status="holiday",
                        remarks="Second/Fourth Saturday Company Off"
                    )
                    db.session.add(att)
                curr += timedelta(days=1)
                continue

            for emp in employees:
                if emp.employment_status == "inactive" and curr > today - timedelta(days=30):
                    continue

                if emp.date_of_joining > curr:
                    continue

                status = random.choice(statuses_weights)

                if status == "present":
                    in_minute = random.randint(45, 59) if random.random() < 0.5 else random.randint(0, 15)
                    in_hour = 8 if in_minute >= 45 else 9
                    check_in = time(in_hour, in_minute)
                    out_hour = random.choice([18, 18, 19, 19, 20])
                    out_minute = random.randint(0, 45)
                    check_out = time(out_hour, out_minute)
                    hours = round((out_hour - in_hour) + (out_minute - in_minute) / 60.0, 2)
                    overtime = round(max(0.0, hours - 8.0), 2)
                    rem = "Regular shift"
                elif status == "late":
                    check_in = time(9, random.randint(31, 55))
                    check_out = time(18, 30)
                    hours = round(9.0 - (check_in.minute / 60.0), 2)
                    overtime = 0.0
                    rem = "Late check-in recorded"
                elif status == "half_day":
                    check_in = time(9, 0)
                    check_out = time(13, 30)
                    hours = 4.5
                    overtime = 0.0
                    rem = "Approved half-day session"
                elif status == "leave":
                    check_in = None
                    check_out = None
                    hours = 0.0
                    overtime = 0.0
                    rem = random.choice(["Paid Casual Leave", "Medical Leave", "Earned Privilege Leave"])
                else:  # absent
                    check_in = None
                    check_out = None
                    hours = 0.0
                    overtime = 0.0
                    rem = "Unexcused absence"

                att = Attendance(
                    employee_id=emp.id,
                    attendance_date=curr,
                    check_in=check_in,
                    check_out=check_out,
                    working_hours=hours,
                    status=status,
                    overtime_hours=overtime,
                    remarks=rem
                )
                db.session.add(att)

            curr += timedelta(days=1)

        db.session.commit()
        print("Attendance records successfully generated.")

        print("5. Generating Multi-Month Payroll Records...")
        from app.services.payroll_service import PayrollService
        payroll_svc = PayrollService()

        # Generate payroll for previous 3 months
        # Determine 3 previous months
        curr_m = today.month
        curr_y = today.year

        for offset in [3, 2, 1]:
            m = curr_m - offset
            y = curr_y
            while m <= 0:
                m += 12
                y -= 1

            result = payroll_svc.generate_monthly_payroll(m, y)
            print(f"Generated payroll for {m}/{y}: {result['generated']} processed, {result['skipped']} skipped.")

            # Mark earlier months as paid and approved
            status_to_set = "paid" if offset > 1 else "approved"
            payrolls = Payroll.query.filter_by(pay_month=m, pay_year=y).all()
            for p in payrolls:
                p.status = status_to_set
                p.approved_by = admin_user.id
                p.approved_at = datetime.utcnow()

        db.session.commit()

        print("6. Generating Performance Evaluations...")
        eval_periods = [
            ("Q3 2023", date(2023, 7, 1), date(2023, 9, 30)),
            ("Q4 2023", date(2023, 10, 1), date(2023, 12, 31)),
            ("Q1 2024", date(2024, 1, 1), date(2024, 3, 31)),
            ("Q2 2024", date(2024, 4, 1), date(2024, 6, 30)),
        ]

        feedbacks = [
            "Exceeded goals with exceptional code quality and high team velocity. Consistently demonstrates ownership.",
            "Solid technical execution and prompt delivery across all sprints. Mentors junior teammates effectively.",
            "Met key project deliverables on schedule. Suggest improving test coverage and cross-team documentation.",
            "Strong collaboration during client releases. Punctuality and responsiveness were commendable.",
            "Needs improvement in meeting sprint deadlines and adhering to architectural quality benchmarks."
        ]

        for emp in employees:
            if emp.employment_status == "inactive":
                continue

            for period_name, p_start, p_end in eval_periods:
                if emp.date_of_joining > p_start:
                    continue

                assigned = random.randint(12, 28)
                comp_pct = random.uniform(0.70, 1.0)
                completed = int(round(assigned * comp_pct))
                quality = round(random.uniform(68.0, 98.0), 1)
                punc = round(random.uniform(70.0, 99.0), 1)
                team = round(random.uniform(72.0, 98.0), 1)
                feedback = random.choice(feedbacks)

                pe = PerformanceEvaluation(
                    employee_id=emp.id,
                    evaluation_period=period_name,
                    period_start=p_start,
                    period_end=p_end,
                    tasks_assigned=assigned,
                    tasks_completed=completed,
                    quality_score=quality,
                    punctuality_score=punc,
                    teamwork_score=team,
                    manager_feedback=feedback,
                    evaluated_by=admin_user.id
                )
                pe.calculate_scores()
                db.session.add(pe)

        # Audit logs for realism
        db.session.add(AuditLog(
            user_id=admin_user.id,
            action="system initialization and seed data load",
            entity_type="system",
            details="Populated organizational structure, employees, attendance, payroll, and evaluations."
        ))

        db.session.commit()
        print("\nAll database seeding completed successfully!")
        print("="*60)
        print("Login Credentials:")
        print("  Administrator: admin@eppas.com    / Admin@123")
        print("  HR Manager:    hr@eppas.com       / Hr@123")
        print("  Employee:      employee@eppas.com / Employee@123")
        print("="*60)

if __name__ == "__main__":
    seed_database()
