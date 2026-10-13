import math
from collections import Counter, defaultdict
from app.models import (
    Book,
    BookCopy,
    Loan,
    Feedback,
    Complaint,
    ImprovementAction,
    PDCACycle,
    RootCauseAnalysis,
    utcnow,
)

MIN_SPC_OBSERVATIONS = 5


def _mean_and_std(values: list[float]):
    """Compute sample mean and sample standard deviation (s)."""
    n = len(values)
    if n == 0:
        return None, None
    mean = sum(values) / n
    if n < 2:
        return round(mean, 2), 0.0
    variance = sum((x - mean) ** 2 for x in values) / (n - 1)
    return round(mean, 2), round(math.sqrt(variance), 2)


def get_customer_satisfaction_metrics() -> dict:
    """Calculate customer satisfaction score, category breakdown, trends, and recurring concerns."""
    feedbacks = Feedback.query.order_by(Feedback.created_at.asc()).all()
    total = len(feedbacks)
    if total == 0:
        return {
            "average_score": None,
            "total_responses": 0,
            "category_averages": {},
            "rating_distribution": {5: 0, 4: 0, 3: 0, 2: 0, 1: 0},
            "trend_labels": [],
            "trend_values": [],
            "recurring_concerns_count": 0,
            "recurring_By_category": {},
        }

    ratings = [f.rating for f in feedbacks]
    avg_score = round(sum(ratings) / total, 2)

    cat_buckets = defaultdict(list)
    dist = {5: 0, 4: 0, 3: 0, 2: 0, 1: 0}
    month_buckets = defaultdict(list)
    recurring_cats = Counter()
    recurring_total = 0

    for f in feedbacks:
        cat_buckets[f.category].append(f.rating)
        dist[f.rating] = dist.get(f.rating, 0) + 1
        period_key = f.created_at.strftime("%Y-%m-%d")
        month_buckets[period_key].append(f.rating)
        if f.is_recurring_concern or f.rating <= 2:
            recurring_total += 1
            recurring_cats[f.category] += 1

    category_averages = {
        cat: {
            "average": round(sum(vals) / len(vals), 2),
            "count": len(vals),
        }
        for cat, vals in cat_buckets.items()
    }

    trend_labels = list(month_buckets.keys())
    trend_values = [round(sum(month_buckets[k]) / len(month_buckets[k]), 2) for k in trend_labels]

    return {
        "average_score": avg_score,
        "total_responses": total,
        "category_averages": category_averages,
        "rating_distribution": dist,
        "trend_labels": trend_labels,
        "trend_values": trend_values,
        "recurring_concerns_count": recurring_total,
        "recurring_by_category": dict(recurring_cats.most_common()),
    }


def get_pareto_analysis() -> dict:
    """Group complaints by category, count frequencies, compute cumulative %, and identify Vital Few."""
    complaints = Complaint.query.all()
    total = len(complaints)
    if total == 0:
        return {
            "total_complaints": 0,
            "categories": [],
            "counts": [],
            "individual_pct": [],
            "cumulative_pct": [],
            "vital_few_categories": [],
            "table_rows": [],
        }

    counts_map = Counter(c.category for c in complaints)
    sorted_items = counts_map.most_common()

    categories = []
    counts = []
    individual_pct = []
    cumulative_pct = []
    vital_few = []
    table_rows = []

    running_count = 0
    for idx, (cat, count) in enumerate(sorted_items):
        running_count += count
        ind_p = round((count / total) * 100, 1)
        cum_p = round((running_count / total) * 100, 1)
        # First category or categories bringing cumulative up to ~80% threshold
        is_vital = (cum_p <= 80.0) or (idx == 0)

        categories.append(cat)
        counts.append(count)
        individual_pct.append(ind_p)
        cumulative_pct.append(cum_p)
        if is_vital:
            vital_few.append(cat)

        table_rows.append(
            {
                "category": cat,
                "count": count,
                "individual_pct": ind_p,
                "cumulative_pct": cum_p,
                "is_vital_few": is_vital,
            }
        )

    return {
        "total_complaints": total,
        "categories": categories,
        "counts": counts,
        "individual_pct": individual_pct,
        "cumulative_pct": cumulative_pct,
        "vital_few_categories": vital_few,
        "table_rows": table_rows,
    }


def _build_spc_series(
    name: str,
    unit: str,
    labels: list[str],
    values: list[float],
    business_target: float,
    target_direction: str,
    min_bound: float = 0.0,
    max_bound: float = None,
) -> dict:
    """Compute statistical control limits (mean +/- 3*s) distinct from business target."""
    n = len(values)
    if n < MIN_SPC_OBSERVATIONS:
        mean_val, std_val = _mean_and_std(values)
        return {
            "name": name,
            "unit": unit,
            "observations_count": n,
            "sufficient_data": False,
            "statistical_status": f"Insufficient Data (n={n} < {MIN_SPC_OBSERVATIONS} minimum observations required)",
            "in_statistical_control": None,
            "labels": labels,
            "values": values,
            "mean": mean_val,
            "std_dev": std_val,
            "ucl": None,
            "lcl": None,
            "business_target": business_target,
            "target_direction": target_direction,
            "out_of_control_points": 0,
        }

    mean_val, std_val = _mean_and_std(values)
    raw_ucl = mean_val + 3.0 * std_val
    raw_lcl = mean_val - 3.0 * std_val

    ucl = round(min(max_bound, raw_ucl) if max_bound is not None else raw_ucl, 2)
    lcl = round(max(min_bound, raw_lcl) if min_bound is not None else raw_lcl, 2)

    out_of_control = sum(1 for v in values if v > ucl or v < lcl)
    in_control = out_of_control == 0

    if in_control:
        status_label = (
            f"Within 3-Sigma Statistical Limits (Preliminary n={n})"
            if n < 20
            else f"Statistically In Control (n={n})"
        )
    else:
        status_label = f"Out of Statistical Control ({out_of_control} special-cause variation point(s))"

    return {
        "name": name,
        "unit": unit,
        "observations_count": n,
        "sufficient_data": True,
        "statistical_status": status_label,
        "in_statistical_control": in_control,
        "labels": labels,
        "values": values,
        "mean": mean_val,
        "std_dev": std_val,
        "ucl": ucl,
        "lcl": lcl,
        "business_target": business_target,
        "target_direction": target_direction,
        "out_of_control_points": out_of_control,
    }


def get_control_charts_data() -> dict:
    """Build 4 Statistical Quality Control Charts from actual database observations."""
    # 1. Customer Satisfaction Over Time
    feedbacks = Feedback.query.order_by(Feedback.created_at.asc()).all()
    sat_labels = [f"FB-{f.id} ({f.created_at.strftime('%m/%d')})" for f in feedbacks]
    sat_values = [float(f.rating) for f in feedbacks]
    satisfaction_spc = _build_spc_series(
        name="Customer Satisfaction Score",
        unit="Rating (1-5)",
        labels=sat_labels,
        values=sat_values,
        business_target=4.2,
        target_direction=">= 4.2 / 5.0",
        min_bound=1.0,
        max_bound=5.0,
    )

    # 2. Book Issue Service Processing Time
    loans = Loan.query.order_by(Loan.issue_date.asc()).all()
    proc_labels = [f"LN-{ln.id} ({ln.issue_date.strftime('%m/%d')})" for ln in loans if ln.processing_time_seconds]
    proc_values = [round(float(ln.processing_time_seconds), 1) for ln in loans if ln.processing_time_seconds]
    processing_spc = _build_spc_series(
        name="Book Issue Service Processing Time",
        unit="Seconds",
        labels=proc_labels,
        values=proc_values,
        business_target=45.0,
        target_direction="<= 45.0 sec",
        min_bound=5.0,
    )

    # 3. Complaint Resolution Time (Hours)
    resolved_complaints = (
        Complaint.query.filter(Complaint.resolved_at.isnot(None))
        .order_by(Complaint.resolved_at.asc())
        .all()
    )
    res_labels = [f"CMP-{c.id} ({c.resolved_at.strftime('%m/%d')})" for c in resolved_complaints]
    res_values = [float(c.resolution_hours) for c in resolved_complaints if c.resolution_hours is not None]
    resolution_spc = _build_spc_series(
        name="Complaint Resolution Lead Time",
        unit="Hours",
        labels=res_labels,
        values=res_values,
        business_target=48.0,
        target_direction="<= 48.0 hrs",
        min_bound=0.0,
    )

    # 4. Overdue-Loan Rate by Cohort / Week
    cohort_buckets = defaultdict(lambda: {"total": 0, "overdue": 0})
    for ln in loans:
        # Group by ISO year-week
        iso_yr, iso_wk, _ = ln.issue_date.isocalendar()
        key = f"{iso_yr}-W{iso_wk:02d}"
        cohort_buckets[key]["total"] += 1
        if ln.is_overdue:
            cohort_buckets[key]["overdue"] += 1

    od_labels = sorted(cohort_buckets.keys())
    od_values = [
        round((cohort_buckets[k]["overdue"] / cohort_buckets[k]["total"]) * 100.0, 1)
        for k in od_labels
        if cohort_buckets[k]["total"] > 0
    ]
    overdue_spc = _build_spc_series(
        name="Weekly Cohort Overdue-Loan Rate",
        unit="%",
        labels=od_labels,
        values=od_values,
        business_target=10.0,
        target_direction="<= 10.0%",
        min_bound=0.0,
        max_bound=100.0,
    )

    return {
        "satisfaction": satisfaction_spc,
        "processing_time": processing_spc,
        "complaint_resolution": resolution_spc,
        "overdue_rate": overdue_spc,
    }


def get_all_kpis() -> list[dict]:
    """Calculate all 10 required TQM KPIs with formula, period, data source, and honest data handling."""
    now = utcnow()

    # 1. Average Customer Satisfaction
    feedbacks = Feedback.query.all()
    fb_count = len(feedbacks)
    avg_sat = round(sum(f.rating for f in feedbacks) / fb_count, 2) if fb_count > 0 else None

    # 2. Book Availability Rate
    active_copies = BookCopy.query.filter(BookCopy.status != "Archived").all()
    total_copies = len(active_copies)
    available_copies = sum(1 for c in active_copies if c.status == "Available")
    avail_rate = round((available_copies / total_copies) * 100, 1) if total_copies > 0 else None

    # 3. Average Book Issue Processing Time
    loans = Loan.query.all()
    proc_times = [ln.processing_time_seconds for ln in loans if ln.processing_time_seconds is not None]
    avg_proc_time = round(sum(proc_times) / len(proc_times), 1) if proc_times else None

    # 4. Average Complaint Resolution Time & 5. Complaint Resolution Rate
    complaints = Complaint.query.all()
    total_complaints = len(complaints)
    resolved_complaints = [c for c in complaints if c.status in ("Resolved", "Closed") and c.resolution_hours is not None]
    avg_res_hours = (
        round(sum(c.resolution_hours for c in resolved_complaints) / len(resolved_complaints), 1)
        if resolved_complaints
        else None
    )
    res_rate = (
        round((len([c for c in complaints if c.status in ("Resolved", "Closed")]) / total_complaints) * 100, 1)
        if total_complaints > 0
        else None
    )

    # 6. Overdue-Loan Rate
    total_loans = len(loans)
    overdue_loans_count = sum(1 for ln in loans if ln.is_overdue)
    overdue_rate = round((overdue_loans_count / total_loans) * 100, 1) if total_loans > 0 else None

    # 7. Inventory Accuracy
    verified_copies = sum(1 for c in active_copies if c.inventory_verified)
    inv_accuracy = round((verified_copies / total_copies) * 100, 1) if total_copies > 0 else None

    # 8. Improvement Actions Completed On Time
    actions = ImprovementAction.query.all()
    completed_actions = [a for a in actions if a.status == "Completed" and a.completed_date is not None]
    on_time_actions = [a for a in completed_actions if a.is_completed_on_time]
    on_time_rate = (
        round((len(on_time_actions) / len(completed_actions)) * 100, 1)
        if completed_actions
        else None
    )

    # 9. Book Utilization Rate (distinct copies that have been borrowed at least once or are currently issued / total copies)
    distinct_borrowed_copies = len({ln.copy_id for ln in loans})
    utilization_rate = (
        round((distinct_borrowed_copies / total_copies) * 100, 1) if total_copies > 0 else None
    )

    # 10. Borrowing Trends (Last 30 days vs Total)
    thirty_days_ago = now.replace(hour=0, minute=0, second=0, microsecond=0)
    from datetime import timedelta
    recent_cutoff = now - timedelta(days=30)
    recent_loans = sum(1 for ln in loans if ln.issue_date >= recent_cutoff)

    kpis = [
        {
            "id": 1,
            "name": "Average Customer Satisfaction",
            "value": f"{avg_sat} / 5.0" if avg_sat is not None else "Insufficient Data",
            "raw_value": avg_sat,
            "target": ">= 4.2 / 5.0",
            "status": "On Target" if (avg_sat is not None and avg_sat >= 4.2) else ("Needs Attention" if avg_sat is not None else "No Data"),
            "formula": "SUM(Feedback.rating) / COUNT(Feedback.id)",
            "measurement_period": "Cumulative / Rolling All-Time",
            "data_source": f"feedbacks table (n={fb_count} ratings)",
        },
        {
            "id": 2,
            "name": "Book Availability Rate",
            "value": f"{avail_rate}%" if avail_rate is not None else "Insufficient Data",
            "raw_value": avail_rate,
            "target": ">= 75.0%",
            "status": "On Target" if (avail_rate is not None and avail_rate >= 75.0) else ("Needs Attention" if avail_rate is not None else "No Data"),
            "formula": "(COUNT(BookCopy WHERE status='Available') / COUNT(Non-Archived BookCopy)) * 100",
            "measurement_period": "Real-Time Snapshot",
            "data_source": f"book_copies table ({available_copies}/{total_copies} copies)",
        },
        {
            "id": 3,
            "name": "Average Book Issue Processing Time",
            "value": f"{avg_proc_time} sec" if avg_proc_time is not None else "Insufficient Data",
            "raw_value": avg_proc_time,
            "target": "<= 45.0 sec",
            "status": "On Target" if (avg_proc_time is not None and avg_proc_time <= 45.0) else ("Needs Attention" if avg_proc_time is not None else "No Data"),
            "formula": "SUM(Loan.processing_time_seconds) / COUNT(Loan.id)",
            "measurement_period": "All Recorded Circulation Transactions",
            "data_source": f"loans table (n={len(proc_times)} transactions)",
        },
        {
            "id": 4,
            "name": "Average Complaint Resolution Time",
            "value": f"{avg_res_hours} hrs" if avg_res_hours is not None else "Insufficient Data",
            "raw_value": avg_res_hours,
            "target": "<= 48.0 hrs",
            "status": "On Target" if (avg_res_hours is not None and avg_res_hours <= 48.0) else ("Needs Attention" if avg_res_hours is not None else "No Data"),
            "formula": "AVG((Complaint.resolved_at - Complaint.created_at) in hours)",
            "measurement_period": "All Resolved Complaints",
            "data_source": f"complaints table (n={len(resolved_complaints)} resolved)",
        },
        {
            "id": 5,
            "name": "Complaint Resolution Rate",
            "value": f"{res_rate}%" if res_rate is not None else "Insufficient Data",
            "raw_value": res_rate,
            "target": ">= 80.0%",
            "status": "On Target" if (res_rate is not None and res_rate >= 80.0) else ("Needs Attention" if res_rate is not None else "No Data"),
            "formula": "(COUNT(Resolved Complaints) / COUNT(Total Complaints)) * 100",
            "measurement_period": "Cumulative",
            "data_source": f"complaints table ({len(resolved_complaints)}/{total_complaints} complaints)",
        },
        {
            "id": 6,
            "name": "Overdue-Loan Rate",
            "value": f"{overdue_rate}%" if overdue_rate is not None else "Insufficient Data",
            "raw_value": overdue_rate,
            "target": "<= 12.0%",
            "status": "On Target" if (overdue_rate is not None and overdue_rate <= 12.0) else ("Needs Attention" if overdue_rate is not None else "No Data"),
            "formula": "(COUNT(Loans Past Due Date) / COUNT(Total Loans)) * 100",
            "measurement_period": "Cumulative Circulation History",
            "data_source": f"loans table ({overdue_loans_count}/{total_loans} loans)",
        },
        {
            "id": 7,
            "name": "Inventory Accuracy",
            "value": f"{inv_accuracy}%" if inv_accuracy is not None else "Insufficient Data",
            "raw_value": inv_accuracy,
            "target": ">= 98.0%",
            "status": "On Target" if (inv_accuracy is not None and inv_accuracy >= 98.0) else ("Needs Attention" if inv_accuracy is not None else "No Data"),
            "formula": "(COUNT(BookCopy WHERE inventory_verified=True) / COUNT(Active BookCopy)) * 100",
            "measurement_period": "Latest Physical Shelf Audit",
            "data_source": f"book_copies table ({verified_copies}/{total_copies} verified)",
        },
        {
            "id": 8,
            "name": "Improvement Actions Completed On Time",
            "value": f"{on_time_rate}%" if on_time_rate is not None else "Insufficient Data",
            "raw_value": on_time_rate,
            "target": ">= 85.0%",
            "status": "On Target" if (on_time_rate is not None and on_time_rate >= 85.0) else ("Needs Attention" if on_time_rate is not None else "No Data"),
            "formula": "(COUNT(Completed Actions WHERE completed_date <= target_date) / COUNT(Completed Actions)) * 100",
            "measurement_period": "Cumulative Kaizen Register",
            "data_source": f"improvement_actions table ({len(on_time_actions)}/{len(completed_actions)} completed)",
        },
        {
            "id": 9,
            "name": "Book Utilization Rate",
            "value": f"{utilization_rate}%" if utilization_rate is not None else "Insufficient Data",
            "raw_value": utilization_rate,
            "target": ">= 40.0%",
            "status": "On Target" if (utilization_rate is not None and utilization_rate >= 40.0) else ("Needs Attention" if utilization_rate is not None else "No Data"),
            "formula": "(COUNT(DISTINCT Loan.copy_id) / COUNT(Active BookCopy)) * 100",
            "measurement_period": "Cumulative Catalog Circulation",
            "data_source": f"loans & book_copies tables ({distinct_borrowed_copies}/{total_copies} copies circulated)",
        },
        {
            "id": 10,
            "name": "Borrowing Trends (30-Day Velocity)",
            "value": f"{recent_loans} loans / 30d" if total_loans > 0 else "Insufficient Data",
            "raw_value": recent_loans,
            "target": ">= 15 loans / 30d",
            "status": "On Target" if recent_loans >= 15 else ("Needs Attention" if total_loans > 0 else "No Data"),
            "formula": "COUNT(Loan WHERE issue_date >= NOW() - 30 days)",
            "measurement_period": "Rolling 30-Day Window",
            "data_source": f"loans table ({recent_loans} in last 30d, {total_loans} total)",
        },
    ]
    return kpis


def get_borrowing_trend_chart() -> dict:
    """Group loans by week/date for borrowing trend visualization."""
    loans = Loan.query.order_by(Loan.issue_date.asc()).all()
    buckets = defaultdict(lambda: {"issued": 0, "returned": 0})
    for ln in loans:
        iso_yr, iso_wk, _ = ln.issue_date.isocalendar()
        key = f"{iso_yr}-W{iso_wk:02d}"
        buckets[key]["issued"] += 1
        if ln.return_date:
            buckets[key]["returned"] += 1

    labels = sorted(buckets.keys())
    return {
        "labels": labels,
        "issued": [buckets[k]["issued"] for k in labels],
        "returned": [buckets[k]["returned"] for k in labels],
    }
