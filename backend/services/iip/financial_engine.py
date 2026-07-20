"""
Financial Intelligence Engine — derived from grant amounts and activity data.
"""
from datetime import datetime, timezone


async def get_financial_overview(institution: str, db) -> dict:
    users = await db.users.find({"institution": institution}, {"_id": 1, "department": 1}).to_list(length=2000)
    uids = [str(u["_id"]) for u in users]
    uid_to_dept = {str(u["_id"]): (u.get("department") or "Unknown") for u in users}
    yr = datetime.now().year

    all_grants = await db.grant_applications.find(
        {"user_id": {"$in": uids}},
        {"user_id": 1, "funder": 1, "amount": 1, "status": 1, "year": 1},
    ).to_list(length=5000)

    approved = [g for g in all_grants if g.get("status") in ("approved", "funded", "active", "granted")]
    total_income = sum(float(g.get("amount") or 0) for g in approved)
    current_yr_income = sum(float(g.get("amount") or 0) for g in approved if g.get("year") == yr)
    prev_yr_income = sum(float(g.get("amount") or 0) for g in approved if g.get("year") == yr - 1)

    # By department
    dept_income: dict = {}
    for g in approved:
        dept = uid_to_dept.get(g.get("user_id", ""), "Unknown")
        dept_income[dept] = dept_income.get(dept, 0) + float(g.get("amount") or 0)

    # By funder
    funder_income: dict = {}
    for g in approved:
        f = g.get("funder", "Unknown")
        funder_income[f] = funder_income.get(f, 0) + float(g.get("amount") or 0)
    top_funders = sorted(funder_income.items(), key=lambda x: -x[1])[:10]

    # Year-on-year income
    income_by_year: dict = {}
    for g in approved:
        y = str(g.get("year", ""))
        if y:
            income_by_year[y] = income_by_year.get(y, 0) + float(g.get("amount") or 0)

    growth = round((current_yr_income - prev_yr_income) / max(prev_yr_income, 1) * 100, 1) if prev_yr_income else 0

    # Funding concentration (Herfindahl-style)
    if total_income > 0:
        shares = [(v / total_income) ** 2 for v in funder_income.values()]
        concentration = round(sum(shares), 4)
        risk = "high" if concentration > 0.5 else ("medium" if concentration > 0.25 else "low")
    else:
        concentration, risk = 0, "low"

    return {
        "institution": institution,
        "total_research_income": round(total_income, 2),
        "current_year_income": round(current_yr_income, 2),
        "previous_year_income": round(prev_yr_income, 2),
        "income_growth_pct": growth,
        "active_grants_count": len(approved),
        "avg_grant_size": round(total_income / len(approved), 2) if approved else 0,
        "income_by_department": [{"department": d, "income": round(v, 2)} for d, v in sorted(dept_income.items(), key=lambda x: -x[1])],
        "top_funding_sources": [{"funder": f, "income": round(v, 2)} for f, v in top_funders],
        "income_by_year": {k: round(v, 2) for k, v in sorted(income_by_year.items())},
        "funding_concentration_index": concentration,
        "funding_dependency_risk": risk,
    }


async def get_financial_by_department(institution: str, db) -> list:
    users = await db.users.find({"institution": institution}, {"_id": 1, "department": 1}).to_list(length=2000)
    depts: dict[str, list] = {}
    for u in users:
        d = u.get("department") or "Unknown"
        depts.setdefault(d, []).append(str(u["_id"]))

    results = []
    for dept, uids in depts.items():
        grants = await db.grant_applications.find(
            {"user_id": {"$in": uids}, "status": {"$in": ["approved", "funded", "active"]}},
            {"amount": 1, "funder": 1},
        ).to_list(length=500)
        income = sum(float(g.get("amount") or 0) for g in grants)
        results.append({
            "department": dept,
            "faculty_count": len(uids),
            "active_grants": len(grants),
            "total_income": round(income, 2),
            "income_per_faculty": round(income / len(uids), 2),
        })
    return sorted(results, key=lambda x: -x["total_income"])
