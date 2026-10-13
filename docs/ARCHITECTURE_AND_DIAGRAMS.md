# System Architecture, Database ER Diagram, and Circulation Workflows

## 1. Layered System Architecture (Mermaid)

```mermaid
flowchart TD
    subgraph Client_Layer["Presentation Layer (HTML5, Bootstrap 5, Chart.js)"]
        AdminUI["Librarian / Admin Workspace"]
        MemberUI["Student / Member Portal"]
        QualityUI["Quality Manager TQM Suite"]
    end

    subgraph Controller_Layer["Flask Blueprints & Security Layer"]
        AuthBP["auth_bp (Sessions, Password Hashing, CSRF)"]
        AdminBP["admin_bp (@role_required('admin'))"]
        MemberBP["member_bp (@role_required('member'))"]
        QualityBP["quality_bp (@role_required('quality_manager', 'admin'))"]
        ReportsBP["reports_bp (CSV Stream Exporters)"]
    end

    subgraph Service_Layer["Domain & TQM Business Logic Layer"]
        LibSvc["library_service.py (Atomic Loans, Returns, Fines, Holds)"]
        TQMSvc["tqm_service.py (10 KPIs, Pareto 80/20, 3-Sigma SPC)"]
        AuditSvc["audit_service.py (Redacted Security Audit Trail)"]
    end

    subgraph Data_Layer["Persistence Layer (SQLAlchemy ORM + Flask-Migrate)"]
        SQLiteDB[("SQLite Relational Database\n(19 Normalized Tables)")]
    end

    AdminUI --> AuthBP & AdminBP & QualityBP & ReportsBP
    MemberUI --> AuthBP & MemberBP
    QualityUI --> AuthBP & QualityBP & ReportsBP

    AdminBP & MemberBP --> LibSvc
    QualityBP & AdminBP & ReportsBP --> TQMSvc
    AuthBP & LibSvc & QualityBP --> AuditSvc

    LibSvc & TQMSvc & AuditSvc --> SQLiteDB
```

---

## 2. Relational Database Entity-Relationship Diagram (Mermaid)

```mermaid
erDiagram
    USER ||--o| MEMBER : "has profile"
    USER ||--o{ NOTIFICATION : "receives"
    USER ||--o{ AUDIT_LOG : "triggers"
    USER ||--o{ STAFF_SUGGESTION : "submits"

    AUTHOR ||--o{ BOOK : "writes"
    PUBLISHER ||--o{ BOOK : "publishes"
    CATEGORY ||--o{ BOOK : "classifies"
    BOOK ||--o{ BOOK_COPY : "has physical copies"
    BOOK ||--o{ RESERVATION : "queued for"
    BOOK ||--o{ FEEDBACK : "rated on"

    MEMBER ||--o{ LOAN : "borrows"
    MEMBER ||--o{ RESERVATION : "places"
    MEMBER ||--o{ FINE : "owes"
    MEMBER ||--o{ FEEDBACK : "submits"
    MEMBER ||--o{ COMPLAINT : "lodges"

    BOOK_COPY ||--o{ LOAN : "circulates in"
    LOAN ||--o| FINE : "incurs"

    COMPLAINT ||--o{ ROOT_CAUSE_ANALYSIS : "investigated by"
    ROOT_CAUSE_ANALYSIS ||--o{ IMPROVEMENT_ACTION : "drives Kaizen"
```

---

## 3. Standardized Book Issue & Return Workflow Diagram (Mermaid)

```mermaid
sequenceDiagram
    actor Librarian
    actor Member
    participant App as Flask / library_service
    participant DB as SQLite (ACID Transaction)

    Note over Librarian,DB: Standardized Book Issue Workflow (SOP-CIRC-01)
    Librarian->>App: Select Available BookCopy + Active Member + Verify TQM Checklist
    App->>DB: Check Copy=='Available', Member=='Active', ActiveLoans < Limit, No Duplicate Title Loan
    alt Validation Fails
        DB-->>App: Raise LibraryOperationError
        App-->>Librarian: Display Validation Error (No State Changed)
    else Validation Passes
        App->>DB: Set BookCopy.status = 'Issued'
        App->>DB: Insert Loan (due_date, processing_time_seconds)
        App->>DB: Fulfill matching Reservation (if any) & Insert Due-Date Notification
        App->>DB: Insert AuditLog('ISSUE_BOOK') & COMMIT
        DB-->>Librarian: Confirm Issue & Due Date
    end

    Note over Librarian,DB: Standardized Book Return Workflow (SOP-CIRC-02)
    Member->>Librarian: Return Physical Book Copy
    Librarian->>App: Submit Return + Physical Condition Inspection (New/Good/Fair/Damaged)
    App->>DB: Set Loan.status = 'Returned', Loan.return_date = NOW()
    alt Condition is 'Damaged'
        App->>DB: Set BookCopy.status = 'Maintenance'
    else Condition is Normal
        App->>DB: Set BookCopy.status = 'Available'
        App->>DB: Promote oldest Pending Reservation to 'Ready' & Notify Member
    end
    alt Returned Past Due Date + Grace Period
        App->>DB: Calculate Fine via Active FinePolicy & Insert Fine + Notification
    end
    App->>DB: Insert AuditLog('RETURN_BOOK') & COMMIT
    DB-->>Librarian: Confirm Return & Fine Assessment
```
