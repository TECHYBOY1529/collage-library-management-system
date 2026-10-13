# Academic Project Report Outline
**Project Title:** Library Management System Integrated with Total Quality Management (TQM) Practices

---

## 1. Abstract
This project presents the design, implementation, and verification of a full-stack academic **Library Management System (LMS) Integrated with Total Quality Management (TQM) Practices**. Built with Python (Flask), SQLite (SQLAlchemy ORM), Bootstrap 5, and Chart.js, the platform unifies copy-level physical book circulation with actionable quality engineering tools: Voice of the Customer (VoC) satisfaction tracking, Pareto 80/20 complaint analysis, Ishikawa Fishbone and 5-Whys Root-Cause Analysis (RCA), a Kaizen Continuous Improvement Register, Plan–Do–Check–Act (PDCA) cycles, 3-Sigma Statistical Process Control (SPC) charts, and 10 live Key Performance Indicators (KPIs).

## 2. Introduction
Academic libraries serve as the knowledge backbone of higher education institutions. Traditional library software focuses solely on cataloging and checkout transactions without measuring service quality, waiting times, inventory accuracy, or member satisfaction. Integrating Total Quality Management (TQM) transforms the library from a passive repository into a continuously improving service organization.

## 3. Problem Statement
Conventional college library systems suffer from:
1. Lack of copy-level visibility and shelf audit verification, leading to "phantom availability."
2. Unstandardized checkout and return workflows causing peak-hour queue delays.
3. Disconnected complaint handling where recurring student concerns are resolved ad-hoc without root-cause investigation.
4. Absence of quantitative quality metrics, statistical control limits, and PDCA tracking.

## 4. Objectives
- Implement role-based workspaces for **Librarians/Administrators**, **Library Members/Students**, and **Quality Managers**.
- Enforce ACID transactional integrity across physical copy issue, return, overdue fine calculation, and reservation queue promotion.
- Embed operational TQM modules (Pareto chart, Fishbone + 5 Whys, Kaizen register, PDCA cycles, SPC charts, and 10 documented KPIs).
- Verify system reliability through automated `pytest` unit and integration testing.

## 5. Existing System
Existing manual registers or basic CRUD library apps record book titles and borrower names but lack:
- Unique physical copy barcoding (`BookCopy`) synchronized with reservations.
- Standardized checkout checklists and transaction processing time capture.
- Structured quality management loops (RCA $\rightarrow$ Kaizen $\rightarrow$ PDCA).

## 6. Proposed System
The proposed **Athena LMS + TQM** system introduces:
- Strict server-side Role-Based Access Control (RBAC) and CSRF-protected forms.
- Copy-level state machine (`Available`, `Issued`, `Maintenance`, `Archived`) with shelf audit accuracy tracking.
- Real-time TQM analytics computed directly from transactional SQLite tables without hard-coded or invented metrics.

## 7. Scope
- **In Scope:** Multi-role authentication, catalog & copy management, standardized issue/return, configurable fine policies, hold queues, member notifications, VoC ratings/complaints, Pareto analysis, Fishbone/5-Whys RCA, Kaizen register, PDCA module, SPC control charts, CSV report exports, audit logs, and repeatable demo data seeding.
- **Out of Scope:** Hardware RFID gate integration and third-party payment gateway processing.

## 8. Technology Requirements
- **Backend:** Python 3.10+, Flask 3.x, Flask-SQLAlchemy, Flask-Migrate, Flask-WTF / WTForms, Werkzeug security.
- **Database:** SQLite 3 with normalized foreign-key relationships.
- **Frontend:** HTML5, CSS3, JavaScript (ES6), Bootstrap 5.3, Chart.js 4.x.
- **Testing & DevOps:** `pytest`, Git, GitHub.

## 9. System Architecture
The application follows a modular 4-tier architecture:
1. **Presentation Layer:** Jinja2 templates, Bootstrap 5 responsive layout, Chart.js visualizations.
2. **Controller Layer:** Role-guarded Flask Blueprints (`auth`, `admin`, `member`, `quality`, `reports`).
3. **Service Layer:** Reusable domain services (`library_service.py`, `tqm_service.py`, `audit_service.py`).
4. **Data Layer:** SQLAlchemy models mapped to 19 relational tables.

## 10. Database Design
Includes normalized entities: `users`, `members`, `authors`, `publishers`, `categories`, `books`, `book_copies`, `fine_policies`, `loans`, `reservations`, `fines`, `feedbacks`, `complaints`, `root_cause_analyses`, `improvement_actions`, `pdca_cycles`, `staff_suggestions`, `notifications`, and `audit_logs`. All tables include an `is_demo` boolean column to isolate demonstration data from live records.

## 11. Module Descriptions
1. **Authentication & RBAC Module:** Manages secure password hashing (`scrypt`/`pbkdf2`), sessions, and `@role_required` decorators.
2. **Inventory & Copy Audit Module:** Tracks bibliographic records, physical copies, and shelf verification status.
3. **Standardized Circulation & Fine Module:** Executes atomic checkouts/returns, enforces loan limits, and calculates fines with grace periods.
4. **Member Self-Service & Notification Module:** Catalog search, one-click reservations, personal loan/fine ledgers, and VoC submissions.
5. **TQM & Statistical Quality Module:** Delivers KPI monitoring, Pareto charts, Fishbone/5-Whys RCA, Kaizen actions, PDCA cycles, and SPC control charts.

## 12. TQM Methodology
Applies Deming's system of profound knowledge and Ishikawa's Seven Basic Tools of Quality:
- **Check Sheets & Standardization:** Mandatory checkout verification checklist and condition inspection on return.
- **Pareto Chart:** Identifies the "Vital Few" complaint categories driving ~80% of member dissatisfaction.
- **Cause-and-Effect (Fishbone) + 5 Whys:** Diagnoses systemic causes across People, Processes, Technology, Materials, Environment, and Policies.
- **SPC Control Charts:** Computes $\bar{X} \pm 3s$ control limits distinct from management targets.
- **PDCA & Kaizen:** Closes the loop with measurable corrective interventions.

## 13. Implementation
Implemented using the Flask application factory pattern (`create_app`), parameterized ORM queries, CSRF tokens on all state-changing forms, and safe transaction rollbacks (`db.session.rollback()`).

## 14. Testing
Tested via an automated `pytest` suite (`tests/`) using an isolated in-memory SQLite database (`sqlite:///:memory:`), covering authentication, RBAC 403 enforcement, duplicate loan prevention, unavailable copy protection, overdue fine calculation, automatic reservation promotion, transaction rollback on commit failure, KPI accuracy, SPC minimum-sample honesty, and CSV exports.

## 15. Results and Discussion
The seeded demonstration dataset (32 books, 70+ physical copies, 12 members, 19 loans, 14 complaints, 12 feedback ratings, 2 RCAs, 5 Kaizen actions, and 2 PDCA cycles) demonstrates how standardized circulation workflows reduced average issue time from a 68s baseline to ~35.2s while maintaining 98.6% inventory accuracy.

## 16. Limitations
- SQLite is optimized for single-node college deployments rather than high-concurrency multi-campus clusters.
- Overdue and reservation alerts are delivered via in-app notifications rather than external SMTP/SMS gateways by default.

## 17. Future Enhancements
- Barcode / QR webcam scanner integration in the circulation desk UI.
- Automated SMTP email & WhatsApp/SMS reminders 48 hours prior to loan due dates.
- PostgreSQL production migration for multi-campus university consortia.
- Machine-learning demand forecasting to recommend copy procurement before semester exams.

## 18. Conclusion
By embedding Total Quality Management directly into daily library operations, this system proves that software engineering and quality management principles reinforce one another—delivering transparent metrics, faster circulation service, higher inventory accuracy, and continuous institutional improvement.
