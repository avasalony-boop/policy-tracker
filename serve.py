import os
from datetime import date, datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, JSONResponse
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///policy_radar.db")
engine = create_engine(DATABASE_URL, future=True)

app = FastAPI(title="Policy Radar")

def effective_status(eff_date: str | None) -> str:
    if not eff_date:
        return "unknown"
    try:
        d = datetime.fromisoformat(eff_date).date()
    except Exception:
        return "unknown"
    today = date.today()
    if d <= today:
        return "active"
    elif (d - today).days <= 90:
        return "effective soon"
    else:
        return "scheduled"

@app.get("/bills")
def list_bills(topic: str = "", state: str = "", status: str = "", limit: int = 100):
    where = []
    params = {}
    if topic:
        where.append("EXISTS (SELECT 1 FROM labels l WHERE l.bill_uid=b.bill_uid AND l.topic_labels LIKE :topic)")
        params["topic"] = f"%{topic}%"
    if state:
        where.append("b.jurisdiction=:st")
        params["st"] = state
    if status:
        where.append("b.status_general=:sg")
        params["sg"] = status
    sql = f"""
        SELECT b.bill_uid, b.jurisdiction, b.bill_number, b.title, b.status_general, b.last_action_date,
               b.effective_date, COALESCE(l.topic_labels, '') AS topic_labels
        FROM bills b
        LEFT JOIN labels l ON l.bill_uid=b.bill_uid
        {"WHERE " + " AND ".join(where) if where else ""}
        ORDER BY b.updated_at DESC
        LIMIT :lim
    """
    params["lim"] = limit
    with engine.begin() as conn:
        rows = conn.execute(text(sql), params).mappings().all()
    data = []
    for r in rows:
        d = dict(r)
        d["effective_status"] = effective_status(d.get("effective_date"))
        data.append(d)
    return JSONResponse(data)

@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request, topic: str = "", state: str = "", status: str = "", limit: int = 100, only_effective_soon: int = 0):
    base_sql = """
        SELECT b.bill_uid, b.jurisdiction, b.bill_number, b.title, b.status_general,
               b.last_action_date, b.effective_date, COALESCE(l.topic_labels, '') AS topic_labels
        FROM bills b
        LEFT JOIN labels l ON l.bill_uid=b.bill_uid
        ORDER BY b.updated_at DESC
        LIMIT :lim
    """
    with engine.begin() as conn:
        rows = conn.execute(text(base_sql), {"lim": limit}).mappings().all()

    items = []
    for r in rows:
        topics = (r["topic_labels"] or "").split(",") if r["topic_labels"] else []
        if topic and topic not in topics:
            continue
        if state and state != r["jurisdiction"]:
            continue
        if status and status != r["status_general"]:
            continue
        eff_stat = effective_status(r["effective_date"])
        if only_effective_soon and eff_stat not in ("effective soon", "active"):
            continue
        items.append((r, eff_stat))

    def selected(val, opt):
        return "selected" if str(val) == str(opt) else ""

    html = f"""
    <!doctype html>
    <html>
    <head>
        <meta charset="utf-8" />
        <title>Policy Radar</title>
        <style>
            body {{ font-family: system-ui, -apple-system, Segoe UI, Roboto, sans-serif; margin: 20px; }}
            h1 {{ margin-bottom: 8px; }}
            .filters {{ display: flex; gap: 10px; align-items: center; margin-bottom: 16px; flex-wrap: wrap; }}
            select, input[type=text], button {{ padding: 6px 8px; }}
            table {{ width: 100%; border-collapse: collapse; }}
            th, td {{ border-bottom: 1px solid #eee; padding: 8px; text-align: left; vertical-align: top; }}
            tr:hover {{ background: #fafafa; }}
            .tag {{ display: inline-block; padding: 2px 6px; border-radius: 6px; background: #f1f3f5; margin-right: 6px; font-size: 12px; }}
            .status {{ font-weight: 600; }}
            .pill {{ padding: 2px 6px; border-radius: 999px; font-size: 12px; }}
            .active {{ background: #e3f9e5; color: #046a38; }}
            .soon {{ background: #fff4e5; color: #8a4300; }}
            .unknown {{ background: #f1f3f5; color: #495057; }}
        </style>
    </head>
    <body>
        <h1>Policy Radar</h1>
        <form class="filters" method="get" action="/">
            <label>Topic
                <select name="topic">
                    <option value="" {selected(topic,"")}>All</option>
                    <option value="ai" {selected(topic,"ai")}>AI</option>
                    <option value="privacy" {selected(topic,"privacy")}>Privacy</option>
                    <option value="housing" {selected(topic,"housing")}>Housing</option>
                    <option value="healthcare" {selected(topic,"healthcare")}>Healthcare</option>
                </select>
            </label>
            <label>State
                <input type="text" name="state" value="{state}" placeholder="e.g., CA, New York" />
            </label>
            <label>Status
                <select name="status">
                    <option value="" {selected(status,"")}>Any</option>
                    <option value="INTRODUCED" {selected(status,"INTRODUCED")}>Introduced</option>
                    <option value="IN_COMMITTEE" {selected(status,"IN_COMMITTEE")}>In Committee</option>
                    <option value="REPORTED" {selected(status,"REPORTED")}>Reported</option>
                    <option value="ON_FLOOR" {selected(status,"ON_FLOOR")}>On Floor</option>
                    <option value="PASSED_LEGISLATURE" {selected(status,"PASSED_LEGISLATURE")}>Passed Legislature</option>
                    <option value="ENACTED" {selected(status,"ENACTED")}>Enacted</option>
                    <option value="VETOED" {selected(status,"VETOED")}>Vetoed</option>
                    <option value="FAILED_DEAD" {selected(status,"FAILED_DEAD")}>Failed/Dead</option>
                </select>
            </label>
            <label><input type="checkbox" name="only_effective_soon" value="1" { "checked" if only_effective_soon else "" }/> Only effective now/soon</label>
            <button type="submit">Apply</button>
        </form>

        <table>
            <thead>
                <tr>
                    <th>State</th>
                    <th>Bill</th>
                    <th>Title</th>
                    <th>Status</th>
                    <th>Last Action</th>
                    <th>Effective</th>
                    <th>Topics</th>
                </tr>
            </thead>
            <tbody>
    """

    for r, eff_stat in items:
        pill_class = "active" if eff_stat == "active" else ("soon" if eff_stat == "effective soon" else "unknown")
        eff_label = r["effective_date"] or "—"
        topics_html = "".join(f'<span class="tag">{t}</span>' for t in (r["topic_labels"] or "").split(",") if t)
        html += f"""
            <tr>
                <td>{r["jurisdiction"] or ""}</td>
                <td>{r["bill_number"] or ""}</td>
                <td>{(r["title"] or "")[:140]}</td>
                <td class="status">{r["status_general"] or ""}</td>
                <td>{r["last_action_date"] or ""}</td>
                <td><span class="pill {pill_class}">{eff_label}</span></td>
                <td>{topics_html}</td>
            </tr>
        """

    html += """
            </tbody>
        </table>
        <p style="margin-top:12px;color:#666;font-size:12px;">Tip: filter by two-letter postal (e.g., CA) or full state name (e.g., California).</p>
    </body>
    </html>
    """
    return HTMLResponse(html)
