# Total Quality Management (TQM) Methodology & KPI Reference Guide

## 1. Implemented TQM Pillars

### A. Customer Focus (Voice of the Customer)
- Library members rate library services on a **1 to 5 scale** across structured quality dimensions:
  - `Book Availability`, `Staff Service`, `Waiting Time`, `Digital Access`, `Cleanliness`, `Study Environment`, and `Other`.
- Members can flag whether an issue is a **recurring concern**.
- The TQM Dashboard computes overall satisfaction, per-category averages, longitudinal satisfaction trends, and recurring issue counts directly from the `feedbacks` table.

### B. Continuous Improvement (Kaizen Register)
- Implemented in the `improvement_actions` table and `/quality/kaizen` route.
- Tracks: Problem description, Identified root cause, Proposed corrective action, Assigned owner, Priority (`Low`, `Medium`, `High`, `Critical`), Target completion date, Completed date, Expected result, Measured result, and Completion notes.
- Automatically classifies actions into `Open`, `In Progress`, `Overdue` (when `NOW() > target_completion_date` and not completed), and `Completed`.

### C. Plan–Do–Check–Act (PDCA Deming Cycle)
- Implemented in the `pdca_cycles` table and `/quality/pdca` route.
- **PLAN**: Problem statement, baseline metric, target metric, and measurement method.
- **DO**: Intervention details, assigned owner, and implementation timestamps.
- **CHECK**: Measured outcome, baseline-vs-target comparison analysis, and boolean target achievement.
- **ACT**: Standardization into library SOPs and next-cycle recommendations.

### D. Pareto 80/20 Analysis
- Groups member complaints in `complaints` by category, sorts descending by frequency, calculates individual and cumulative percentages, and highlights the **Vital Few** categories responsible for the majority (~80%) of complaints.

### E. Root-Cause Analysis (Ishikawa Fishbone + 5 Whys)
- Implemented in `root_cause_analyses` and `/quality/rca`.
- Captures all 6 Fishbone categories (**People**, **Processes**, **Technology**, **Materials and resources**, **Environment**, **Policies and procedures**) alongside a 5-step **5 Whys** causal chain.

### F. Statistical Process Control (SPC) Charts
- Tracks 4 operational quality measures over time:
  1. Customer Satisfaction Score (`Rating 1–5`)
  2. Book Issue Service Processing Time (`Seconds`)
  3. Complaint Resolution Lead Time (`Hours`)
  4. Weekly Cohort Overdue-Loan Rate (`%`)
- Computes sample mean ($\bar{X}$), sample standard deviation ($s$), **Upper Control Limit ($\text{UCL} = \bar{X} + 3s$)**, and **Lower Control Limit ($\text{LCL} = \max(0, \bar{X} - 3s)$)**.
- Strictly separates statistical control limits from management **Business Targets**, and never declares a process statistically in control when $n < 5$ observations exist.

---

## 2. Ten Key Performance Indicators (KPIs) — Formulas & Definitions

| # | KPI Name | Mathematical Formula | Measurement Period | Database Source |
|---|----------|----------------------|--------------------|-----------------|
| 1 | **Average Customer Satisfaction** | $\frac{\sum \text{Feedback.rating}}{\text{COUNT(Feedback.id)}}$ | Cumulative / Rolling All-Time | `feedbacks` table |
| 2 | **Book Availability Rate** | $\frac{\text{COUNT(BookCopy WHERE status='Available')}}{\text{COUNT(BookCopy WHERE status!='Archived')}} \times 100$ | Real-Time Snapshot | `book_copies` table |
| 3 | **Average Book Issue Processing Time** | $\frac{\sum \text{Loan.processing\_time\_seconds}}{\text{COUNT(Loan.id)}}$ | All Recorded Circulation Transactions | `loans` table |
| 4 | **Average Complaint Resolution Time** | $\text{AVG}\left(\frac{\text{Complaint.resolved\_at} - \text{Complaint.created\_at}}{3600\text{s}}\right)$ | All Resolved Complaints | `complaints` table |
| 5 | **Complaint Resolution Rate** | $\frac{\text{COUNT(Complaint WHERE status IN ('Resolved','Closed'))}}{\text{COUNT(Complaint.id)}} \times 100$ | Cumulative | `complaints` table |
| 6 | **Overdue-Loan Rate** | $\frac{\text{COUNT(Loans Past Due Date)}}{\text{COUNT(Loan.id)}} \times 100$ | Cumulative Circulation History | `loans` table |
| 7 | **Inventory Accuracy** | $\frac{\text{COUNT(BookCopy WHERE inventory\_verified=True)}}{\text{COUNT(Active BookCopy)}} \times 100$ | Latest Physical Shelf Audit | `book_copies` table |
| 8 | **Improvement Actions Completed On Time** | $\frac{\text{COUNT(Completed Actions WHERE completed\_date} \le \text{target\_date)}}{\text{COUNT(Completed Actions)}} \times 100$ | Cumulative Kaizen Register | `improvement_actions` table |
| 9 | **Book Utilization Rate** | $\frac{\text{COUNT(DISTINCT Loan.copy\_id)}}{\text{COUNT(Active BookCopy)}} \times 100$ | Cumulative Catalog Circulation | `loans`, `book_copies` tables |
| 10 | **Borrowing Trends (30-Day Velocity)** | $\text{COUNT(Loan WHERE issue\_date} \ge \text{NOW()} - 30\text{ days)}$ | Rolling 30-Day Window | `loans` table |
