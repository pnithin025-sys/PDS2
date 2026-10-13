# Employee Performance and Payroll Analytics System (EPPAS)

A full-stack, enterprise-grade HR management and business intelligence platform developed as a semester capstone project. EPPAS integrates employee information management, attendance tracking, automated payroll processing, employee productivity appraisal, statistical analysis (via Pandas and NumPy), and interactive visualization dashboards (via Chart.js).

---

## 🚀 Key Features & Modules

### 1. Authentication & Role-Based Access Control (RBAC)
- **Three Tiered Roles**:
  - `Admin`: Full system administration, user role assignments, audit log tracking.
  - `HR Manager`: Employee lifecycle management, attendance recording/importing, payroll generation/approval, performance evaluations, and document generation.
  - `Employee`: Self-service portal to review individual profile, monthly attendance calendars, and download official PDF salary slips.
- **Security**: Password hashing via Werkzeug (`pbkdf2:sha256`), CSRF protection across all forms (`Flask-WTF`), and session fixation safeguards.

### 2. Employee Information Management
- Complete staff directory with search, department filtering, sorting, and pagination.
- Full employee profile views with compensation structure, reporting manager hierarchy, and employment status history (active/inactive soft-deactivation).
- Department management with active/total headcount monitoring.

### 3. Attendance Tracking & Analytics
- Daily roster marking with rapid batch status setters ("Mark All Present", "Mark All Absent").
- Automated calculation of working hours and overtime hours from check-in and check-out timestamps.
- Color-coded monthly calendar view with per-day badges and monthly summary metrics.
- CSV attendance bulk import engine with validation and error reporting.
- CSV and Excel export utilities.

### 4. Automated Payroll Processing Engine
- Multi-component salary structure: Basic Salary, HRA, Other Allowances, Bonuses, and Overtime Pay.
- Statutory deductions: Configurable Income Tax TDS, Provident Fund (PF), and other deductions.
- **Attendance-Linked Deduction Formula**:
  $$\text{Unpaid Deduction} = \left(\frac{\text{Basic Salary}}{\text{Working Days}}\right) \times \text{Days Absent}$$
- **Overtime Pay Computation**:
  $$\text{Hourly Wage} = \frac{\text{Daily Wage}}{8}, \quad \text{Overtime Pay} = \text{Hourly Wage} \times 1.5 \times \text{Overtime Hours}$$
- Batch monthly payroll execution with idempotency protection.
- Draft $\rightarrow$ Approved $\rightarrow$ Paid workflow with auditor attribution.
- Printable, professional PDF salary slip downloads generated on-the-fly with ReportLab.

### 5. Performance Appraisal & Productivity Scoring
- Multi-dimensional objective scoring algorithm:
  $$\text{Overall Score} = 0.40 \times \text{Task Completion \%} + 0.30 \times \text{Quality} + 0.15 \times \text{Punctuality} + 0.15 \times \text{Teamwork}$$
- Tiered rating classifications:
  - **Excellent**: $90.0 - 100.0$
  - **Good**: $75.0 - 89.9$
  - **Satisfactory**: $60.0 - 74.9$
  - **Needs Improvement**: $< 60.0$
- Real-time live score calculator on the evaluation entry form.
- Top performers organization leaderboard with medal rankings.

### 6. Interactive Dashboards & Statistical Analytics
- Real-time executive KPIs: Active Headcount, Today's Attendance, Average Attendance Rate, Monthly Payroll Spend, and Mean Performance Score.
- **8 Dynamic Chart.js Visualizations**:
  1. Monthly Attendance Trend (Line Chart)
  2. Salary Distribution Histogram (Bar Chart)
  3. Department-wise Payroll Allocation (Bar Chart)
  4. Performance Tier Distribution (Pie Chart)
  5. Attendance Status Breakdown (Doughnut Chart)
  6. Department Headcount Comparison (Polar Area Chart)
  7. 6-Month Payroll Expense Trend (Area Line Chart)
  8. Performance vs. Attendance Correlation (Scatter Chart)
- Detailed statistical analysis page powered by Pandas and NumPy ($\mu$, median, min, max, variance).

### 7. Executive Reports & Document Center
- Multi-format document generation:
  - **PDF Documents** (ReportLab): Employee Directory, Attendance Register, Payroll Summary, Performance Report, Individual Salary Slips.
  - **Excel Spreadsheets (.xlsx)** (Pandas + openpyxl): Clean formatted tables for business analysis.
  - **CSV Exports**: Streamed raw data for data pipelines.

---

## 🛠️ Technology Stack

- **Backend**: Python 3.11, Flask 3.0, Flask-Login, Flask-SQLAlchemy 3.1, Flask-Migrate, Flask-WTF
- **Database**: SQLite (SQLAlchemy ORM with Foreign Keys, Cascades, and Unique Constraints)
- **Data Science & Analytics**: Pandas 2.1, NumPy 1.26
- **Document Generation**: ReportLab 4.0, openpyxl 3.1
- **Testing**: PyTest 7.4 (19 automated unit & integration tests)
- **Frontend**: Semantic HTML5, Vanilla CSS3 (Custom Design System with Light/Dark Themes), Chart.js 4.4, Bootstrap Icons 1.11

---

## 📦 Installation & Setup

### 1. Clone & Enter Directory
```bash
cd "e:\III sem capstorn project\PDS"
```

### 2. Activate Virtual Environment
```powershell
.\.venv\Scripts\Activate.ps1
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Seed the Database
Populate the database with 52 realistic employee profiles, 7 departments, 90 days of attendance logs, 3 months of payroll runs, and quarterly evaluations:
```bash
python seed_data.py
```

### 5. Run the Application
```bash
python run.py
```
Open your browser and navigate to: **`http://127.0.0.1:5000`**

---

## 🔑 Demo Login Credentials

| Role | Email | Password | Access Privileges |
| :--- | :--- | :--- | :--- |
| **System Administrator** | `admin@eppas.com` | `Admin@123` | Full access, user roles, audit trails |
| **HR Manager** | `hr@eppas.com` | `Hr@123` | Employees, Attendance, Payroll, Performance, Reports |
| **Employee** | `employee@eppas.com` | `Employee@123` | Self profile, attendance calendar, salary slips |

---

## 🧪 Running Automated Tests

Run the complete 19-test suite:
```bash
python -m pytest -v
```

---

## 📂 Project Structure

```
PDS/
├── app/
│   ├── __init__.py           # Flask app factory, blueprints, error handlers
│   ├── extensions.py         # SQLAlchemy, LoginManager, CSRFProtect, Migrate
│   ├── models.py             # User, Department, Employee, Attendance, Payroll, Evaluation, AuditLog
│   ├── analytics/            # Analytics blueprint & JSON API routes
│   ├── attendance/           # Daily marking, CSV import/export, monthly calendar
│   ├── auth/                 # Login, register, profile, user management
│   ├── employees/            # Employee CRUD, department management
│   ├── payroll/              # Monthly generation, approvals, salary slip PDFs
│   ├── performance/          # Evaluations, scoring engine, leaderboard
│   ├── reports/              # PDF, Excel, and CSV report hub
│   ├── services/
│   │   ├── analytics_service.py # Pandas & NumPy computation engine
│   │   ├── payroll_service.py   # Salary calculation logic
│   │   └── report_service.py    # ReportLab PDF styling and builders
│   ├── static/
│   │   └── css/style.css     # CSS custom properties, responsive design, dark mode
│   └── templates/            # 23 Jinja2 HTML templates
├── tests/                    # 19 automated Pytest unit tests
├── instance/                 # SQLite database storage
├── config.py                 # Configuration classes (Dev, Testing, Prod)
├── requirements.txt          # Python dependencies
├── run.py                    # Server startup script
├── seed_data.py              # Realistic sample data generator
└── README.md                 # Project documentation
```
