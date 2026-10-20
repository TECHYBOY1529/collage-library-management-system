# College Professor Demonstration & Viva Guide
**Athena LMS + TQM:** Library Management System Integrated with Total Quality Management

---

## 1. Quick Launch Checklist (Before Meeting Your Professor)

1. Open **Windows PowerShell** on your laptop.
2. Navigate to your project folder:
   ```powershell
   cd "D:\COLLEGE LIBRARY MANAGEMENT SYSTEM"
   ```
3. Activate the virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
4. Run the test suite to ensure all tests are green (takes ~20 seconds):
   ```powershell
   pytest tests
   ```
5. Start the web application:
   ```powershell
   python run.py
   ```
6. Open your web browser to: **`http://127.0.0.1:5000`**

---

## 2. Demo Accounts Reference

| Role | Username | Password | Key Showcase Modules |
|------|----------|----------|----------------------|
| **Librarian / Admin** | `admin_demo` | `Admin@123` | Inventory, Copy Barcodes, Issue/Return, Fines, Reservations, Audit Logs |
| **Quality Manager** | `tqm_demo` | `Quality@123` | 10 Live KPIs, Pareto 80/20, Fishbone (6M) RCA, Kaizen, PDCA Cycles, SPC Charts |
| **Student / Member** | `member_demo` | `Member@123` | Catalog Search, Book Reservations, Loan Ledger, VoC Feedback, Complaints |

> **Pro Tip:** On the login screen, click any of the "Quick Academic Demo Evaluators" buttons to automatically fill the username and password with one click!

---

## 3. Recommended 5-Minute Demonstration Script

### Step 1: Student / Member Portal (Showcase User Experience & VoC)
1. Log in as **`member_demo`** (or click the Student button).
2. Show the **Member Dashboard**:
   - Point out active loans, due dates, outstanding fines, and unread notifications.
3. Click **Browse & Search Catalog** (`/member/catalog`):
   - Search for a keyword like `"Machine Learning"` or `"Engineering"`.
   - Filter by Availability or Category.
   - Click **Reserve** on a book to show the automatic queue position.
4. Click **Ratings & Complaints** (`/member/feedback-complaints`):
   - Submit a 5-star rating under `"Book Availability"` (Voice of the Customer).
   - Submit a test complaint under `"Waiting Time"` to demonstrate closed-loop quality management.
5. Click your name in the top right &rarr; show **Account Settings & Profile** (`/profile`) where students can update their contact info and change their password.
6. Click **Logout**.

### Step 2: Circulation & Librarian Desk (Showcase Standardized Operations)
1. Log in as **`admin_demo`**.
2. Show the **Main Admin Dashboard** (`/admin/dashboard`):
   - High-level counter cards: Total Books, Available Copies, Active Loans, Overdue Loans, Pending Complaints, and Satisfaction Score.
3. Click **Book Inventory** (`/admin/books`):
   - Show how each bibliographic record tracks multiple physical copies (`CP-0001-01`, `CP-0001-02`) with specific conditions (`Good`, `Fair`, `Damaged`).
   - Click **Shelf Audit** on any copy to toggle inventory verification.
4. Click **Issue & Return Books** (`/admin/loans`):
   - **Issue a copy:** Select an available book and active member. Emphasize the **Standardized TQM Checkout Checklist** checkbox and **Processing Time (seconds)** input.
   - **Return a copy:** Show condition inspection upon return. Demonstrate that overdue loans automatically calculate fines based on policy and notify the next waiting student in the reservation queue.
5. Click **Audit Logs & Demo Seed** (`/admin/audit-logs`):
   - Show the immutable audit trail recording every checkout, return, shelf audit, and login with user actor stamps and password redaction.

### Step 3: Quality Manager & TQM Analytics (The Core Differentiator)
1. Log in as **`tqm_demo`** (or navigate from Admin menu).
2. Show the **TQM & KPI Dashboard** (`/quality/dashboard`):
   - Explain the **10 Live KPIs** computed dynamically from relational tables (Availability Rate, Issue Processing Time, Complaint Resolution Time, Inventory Accuracy, etc.).
   - Show the **Pareto 80/20 Chart**: Explains which "vital few" complaint categories cause 80% of student dissatisfaction.
   - Show the **Customer Satisfaction Breakdown** by dimension (Staff Service, Cleanliness, Availability, etc.).
3. Click **Root-Cause (Fishbone)** (`/quality/rca`):
   - Present the **Ishikawa Fishbone Diagram** mapping systemic issues across 6 dimensions: **People, Processes, Technology, Materials, Environment, Policies**.
   - Show the **5-Whys Causal Chain** drilling down to the root cause.
4. Click **Kaizen Register** (`/quality/kaizen`):
   - Show corrective action items linked to RCAs with assigned owners, priority, target dates, and real-time status (`Open`, `In Progress`, `Overdue`, `Completed`).
5. Click **PDCA Cycles** (`/quality/pdca`):
   - Walk through a complete **Plan &rarr; Do &rarr; Check &rarr; Act** Deming improvement cycle.
6. Click **SPC Control Charts** (`/quality/control-charts`):
   - Explain the **3-Sigma Statistical Control Limits** ($\text{UCL} = \bar{X} + 3s$, $\text{LCL} = \bar{X} - 3s$).
   - Point out **Sample Size Honesty**: If fewer than 5 observations exist, the chart explicitly reports *"Insufficient Data"* rather than falsely claiming statistical control.
7. Click **Reports & CSV Export** (`/reports/`):
   - Download the **TQM KPIs CSV** or **Inventory CSV** to show export capabilities.

---

## 4. Likely Professor Viva Questions & Model Answers

### Q1: What makes your Library System different from standard CRUD library software?
> **Answer:** Standard library systems only perform basic data entry (book titles and borrower names). Our system embeds **Total Quality Management (TQM)** principles into every workflow:
> 1. It tracks physical inventory at the **copy level** with shelf audit verification.
> 2. It captures operational metrics like **checkout processing times**.
> 3. It closes the loop on student dissatisfaction through **Voice of the Customer ratings, Pareto 80/20 defect analysis, Ishikawa Fishbone root cause analysis, Kaizen corrective actions, and Deming PDCA cycles**.
> 4. It monitors operational consistency using **3-Sigma Statistical Process Control (SPC)** charts.

### Q2: Why did you separate `Book` from `BookCopy`?
> **Answer:** A title (e.g., *Introduction to Algorithms*) has one ISBN, author, and publisher, but the library may own 5 physical copies on different shelves with differing wear conditions. Normalizing the schema into `books` (metadata) and `book_copies` (physical inventory) allows tracking individual barcode labels, shelf audits, repair statuses, and accurate real-time availability.

### Q3: How do the Statistical Process Control (SPC) charts work?
> **Answer:** We compute the sample mean ($\bar{X}$) and sample standard deviation ($s$) across operational samples (e.g., checkout transaction times). We establish upper control limits ($\text{UCL} = \bar{X} + 3s$) and lower control limits ($\text{LCL} = \max(0, \bar{X} - 3s)$). In accordance with quality engineering standards, our system refuses to claim statistical control when $n < 5$ observations exist to prevent false confidence.

### Q4: How is security handled?
> **Answer:**
> - Passwords are never stored in plaintext; they use salted cryptographic hashing via Werkzeug (`scrypt`/`pbkdf2`).
> - Every state-changing form is protected against Cross-Site Request Forgery (CSRF) via Flask-WTF tokens.
> - Role-Based Access Control (RBAC) is enforced server-side using `@role_required` decorators and session validation.
> - In-memory audit logging redacts credentials and tracks every transaction.

### Q5: How is the system tested?
> **Answer:** We maintain an automated `pytest` test suite that spins up an isolated in-memory SQLite database (`sqlite:///:memory:`). The suite tests RBAC enforcement, loan invariants, duplicate borrowing prevention, fine calculation, hold queue promotion, KPI math, and profile updates. All tests pass with 100% success.
