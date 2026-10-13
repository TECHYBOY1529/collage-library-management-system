# Library Management System Integrated with Total Quality Management (TQM) Practices

A complete, modular, academic **Library Management System (LMS)** integrated with working **Total Quality Management (TQM)** practices—including **Customer Focus (VoC)**, **Kaizen Continuous Improvement**, **PDCA Deming Cycles**, **Pareto 80/20 Complaint Analysis**, **Ishikawa Fishbone & 5-Whys Root-Cause Analysis**, **3-Sigma Statistical Process Control (SPC) Charts**, and **10 Live Key Performance Indicators (KPIs)**.

---

## 1. Technology Stack

- **Backend:** Python 3, Flask, Flask-SQLAlchemy, Flask-Migrate, Flask-WTF / WTForms, Werkzeug Security
- **Database:** SQLite (normalized 19-table relational schema with copy-level inventory tracking)
- **Frontend:** HTML5, CSS3, JavaScript, Bootstrap 5.3, Bootstrap Icons, Chart.js 4
- **Testing:** `pytest` (isolated in-memory SQLite test suite)
- **Automation & Version Control:** Git, GitHub, and `scripts/daily_git_sync.py`

---

## 2. Project Directory Structure

```text
library-management-system-tqm/
├── .env.example                  # Placeholder environment variables
├── .gitignore                    # Excludes secrets, .env, .venv, instance/*.db, caches
├── config.py                     # Development, production, and in-memory testing configs
├── requirements.txt              # Python package dependencies
├── run.py                        # Application entry point (auto-initializes DB & demo seed)
├── seed.py                       # Repeatable demo-data seeder & safe demo-only reset
├── app/
│   ├── __init__.py               # Flask application factory & CLI commands
│   ├── extensions.py             # SQLAlchemy, Migrate, CSRFProtect instances
│   ├── models.py                 # 19 normalized relational models
│   ├── forms.py                  # WTForms server-side validation classes
│   ├── decorators.py             # @login_required and @role_required RBAC guards
│   ├── services/
│   │   ├── audit_service.py      # Redacted security & administrative audit logger
│   │   ├── library_service.py    # Transactional book issue, return, fine & reservation logic
│   │   └── tqm_service.py        # 10 KPIs, Pareto 80/20, Customer Focus & 3-Sigma SPC engine
│   ├── routes/
│   │   ├── auth.py               # Login, registration, logout, role routing
│   │   ├── admin.py              # Librarian dashboard, inventory, loans, fines, audit logs
│   │   ├── member.py             # Student portal, catalog search, holds, feedback/complaints
│   │   ├── quality.py            # TQM dashboard, Kaizen, PDCA, Fishbone RCA, SPC charts
│   │   └── reports.py            # 6 CSV report exporters
│   ├── static/
│   │   ├── css/style.css         # Academic library theme & responsive layout
│   │   └── js/main.js            # Confirmation dialogs & instant table filtering
│   └── templates/                # Role-specific Jinja2 HTML templates
├── tests/                        # Automated pytest suite
│   ├── conftest.py
│   ├── test_auth_and_roles.py
│   ├── test_library_operations.py
│   └── test_tqm_and_reports.py
├── docs/                         # Detailed academic & architecture documentation
│   ├── ARCHITECTURE_AND_DIAGRAMS.md
│   ├── TQM_AND_KPI_GUIDE.md
│   └── PROJECT_REPORT_OUTLINE.md
└── scripts/
    └── daily_git_sync.py         # Verified daily automated Git commit & push script
```

---

## 3. Installation, Database Setup & Execution Instructions

### Step 1: Create and Activate Virtual Environment
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

### Step 2: Install Dependencies
```powershell
pip install -r requirements.txt
```

### Step 3: Configure Environment (Optional)
Copy `.env.example` to `.env` and customize `SECRET_KEY` if desired:
```powershell
Copy-Item .env.example .env
```

### Step 4: Initialize Database & Seed Demonstration Data
You can initialize the SQLite database and populate the labeled academic demonstration dataset (32 fictional books, 70+ physical copies, 12 fictional members, 19 sample loans, 14 Pareto-structured complaints, 12 satisfaction ratings, 2 Fishbone/5-Whys RCAs, 5 Kaizen actions, and 2 PDCA cycles) using either the Flask CLI or `seed.py`:
```powershell
.\.venv\Scripts\flask --app run.py init-db
.\.venv\Scripts\flask --app run.py seed-demo
# Or directly:
.\.venv\Scripts\python seed.py
```
> **Safe Reset Note:** All demo records are tagged with `is_demo=True`. Running `flask --app run.py seed-demo` or `flask --app run.py clear-demo` (or using the Admin UI buttons under **Audit Logs & Demo Seed**) affects **only** demonstration records and never deletes real user accounts or live transactions.

### Step 5: Run the Application
```powershell
.\.venv\Scripts\python run.py
```
Open **`http://127.0.0.1:5000`** in your browser.
On the login screen, you can register a new account or use the local academic evaluator quick-fill buttons for the 3 roles (**Librarian / Admin**, **Quality Manager**, or **Student Member**).

---

## 4. Running Automated Tests (`pytest`)

Execute the complete unit and integration test suite with:
```powershell
.\.venv\Scripts\pytest -v
```

---

## 5. Documentation & Diagrams Index

- **[Architecture, ER Diagram & Workflows](docs/ARCHITECTURE_AND_DIAGRAMS.md)**: Mermaid system architecture, 19-table Entity-Relationship diagram, and standardized book issue/return sequence diagram.
- **[TQM Methodology & 10 KPI Formulas](docs/TQM_AND_KPI_GUIDE.md)**: Detailed formulas, measurement periods, data sources, and SPC 3-sigma rules.
- **[18-Section College Project Report Outline](docs/PROJECT_REPORT_OUTLINE.md)**: Complete academic report structure ready for college submission.
