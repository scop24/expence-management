"""
SpendWise – Student Expense Tracker
====================================
All monetary values are stored in INTEGER PAISE (1 INR = 100 paise) to avoid
floating-point rounding errors.  Display helpers convert back to INR.

To reset demo data:  delete spendwise.db and restart the server.
"""

import csv
import io
import os
import sqlite3
import calendar
from datetime import datetime, date
from flask import (
    Flask, render_template, request, redirect, url_for,
    flash, g, Response
)

# ---------------------------------------------------------------------------
# App setup
# ---------------------------------------------------------------------------

app = Flask(__name__)
# Never hardcode secrets: read from the environment, fall back to a dev key.
app.secret_key = os.environ.get("SECRET_KEY", "spendwise-dev-key-change-me")

DATABASE = os.path.join(os.path.dirname(__file__), "spendwise.db")

CATEGORIES = [
    "Food & Dining",
    "Transport",
    "Stationery & Books",
    "Entertainment",
    "Clothing",
    "Health & Medicine",
    "Rent & Utilities",
    "Mobile & Internet",
    "Miscellaneous",
]

PAYMENT_METHODS = ["UPI", "Cash", "Card", "Net Banking", "Other"]

EXPENSES_PER_PAGE = 15

# ---------------------------------------------------------------------------
# Database helpers
# ---------------------------------------------------------------------------

def get_db():
    """Return a thread-local database connection (opens once per request)."""
    if "db" not in g:
        g.db = sqlite3.connect(DATABASE)
        g.db.row_factory = sqlite3.Row          # access columns by name
        g.db.execute("PRAGMA journal_mode=WAL")  # better concurrency
        ensure_schema(g.db)                      # migrate older databases
    return g.db


@app.teardown_appcontext
def close_db(exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def ensure_schema(db):
    """Create newer tables/columns if an older database is missing them."""
    cols = [r["name"] for r in db.execute("PRAGMA table_info(expenses)").fetchall()]
    if "payment_method" not in cols:
        db.execute("ALTER TABLE expenses ADD COLUMN payment_method TEXT DEFAULT 'UPI'")
    db.execute("""
        CREATE TABLE IF NOT EXISTS category_budgets (
            category  TEXT PRIMARY KEY,
            monthly_p INTEGER NOT NULL DEFAULT 0   -- paise
        )
    """)
    db.commit()


def init_db():
    """Create tables if they don't exist, and optionally seed demo data."""
    db = sqlite3.connect(DATABASE)
    db.row_factory = sqlite3.Row
    db.execute("PRAGMA journal_mode=WAL")

    db.executescript("""
        CREATE TABLE IF NOT EXISTS expenses (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            title       TEXT    NOT NULL,
            amount_p    INTEGER NOT NULL,           -- stored in paise
            category    TEXT    NOT NULL,
            expense_date TEXT   NOT NULL,           -- ISO date: YYYY-MM-DD
            notes       TEXT    DEFAULT '',
            created_at  TEXT    DEFAULT (datetime('now','localtime'))
        );

        CREATE TABLE IF NOT EXISTS budget (
            id          INTEGER PRIMARY KEY CHECK (id = 1),  -- single row
            monthly_p   INTEGER NOT NULL DEFAULT 0           -- paise
        );

        INSERT OR IGNORE INTO budget (id, monthly_p) VALUES (1, 0);
    """)
    ensure_schema(db)

    # Seed demo data only when the table is empty
    count = db.execute("SELECT COUNT(*) FROM expenses").fetchone()[0]
    if count == 0:
        today = date.today()
        month = today.strftime("%Y-%m")
        demo = [
            ("Lunch at Canteen",    12000, "Food & Dining",      f"{month}-02", "Thali + Juice", "UPI"),
            ("Metro Card Recharge", 20000, "Transport",          f"{month}-03", "Monthly pass",  "UPI"),
            ("Algorithm Textbook",  45000, "Stationery & Books", f"{month}-05", "",              "Card"),
            ("Mobile Recharge",     23900, "Mobile & Internet",  f"{month}-07", "28-day plan",   "UPI"),
            ("Movie Ticket",        25000, "Entertainment",      f"{month}-09", "IMAX",          "Card"),
            ("Paracetamol",          5000, "Health & Medicine",  f"{month}-10", "Fever medicine","Cash"),
            ("Dinner Out",          18000, "Food & Dining",      f"{month}-11", "Pizza night",   "UPI"),
            ("Notebook x5",          8500, "Stationery & Books", f"{month}-12", "",              "Cash"),
        ]
        db.executemany(
            "INSERT INTO expenses (title, amount_p, category, expense_date, notes, payment_method)"
            " VALUES (?,?,?,?,?,?)",
            demo,
        )
        # Set a demo budget of ₹3000
        db.execute("UPDATE budget SET monthly_p = 300000 WHERE id = 1")
        db.commit()

    db.close()


# ---------------------------------------------------------------------------
# Utility / formatting helpers
# ---------------------------------------------------------------------------

def paise_to_inr(paise: int) -> float:
    return paise / 100.0


def inr_to_paise(inr_str: str) -> int:
    """Convert an INR string like '120.50' to integer paise (12050)."""
    return round(float(inr_str) * 100)


def fmt_inr(paise: int) -> str:
    """Format paise value as ₹ string with Indian number formatting."""
    rupees = paise / 100.0
    # Build Indian number format (e.g. 1,23,456.78)
    s = f"{rupees:.2f}"
    int_part, dec_part = s.split(".")
    # Indian grouping: last 3 then groups of 2
    if len(int_part) > 3:
        last3 = int_part[-3:]
        rest = int_part[:-3]
        groups = []
        while len(rest) > 2:
            groups.append(rest[-2:])
            rest = rest[:-2]
        groups.append(rest)
        groups.reverse()
        int_part = ",".join(groups) + "," + last3
    return f"₹{int_part}.{dec_part}"


def validate_expense_form(form):
    """Validate add/edit expense form. Returns (errors, cleaned_dict)."""
    title    = form.get("title", "").strip()
    amount_s = form.get("amount", "").strip()
    category = form.get("category", "").strip()
    exp_date = form.get("expense_date", "").strip()
    notes    = form.get("notes", "").strip()
    pay      = form.get("payment_method", "").strip()

    errors = []
    amount_p = None

    if not title:
        errors.append("Title is required.")
    if not amount_s:
        errors.append("Amount is required.")
    else:
        try:
            amount_f = float(amount_s)
            if amount_f <= 0:
                errors.append("Amount must be greater than zero.")
            else:
                amount_p = round(amount_f * 100)
        except ValueError:
            errors.append("Amount must be a valid number.")
    if not category or category not in CATEGORIES:
        errors.append("Please select a valid category.")
    if pay and pay not in PAYMENT_METHODS:
        errors.append("Please select a valid payment method.")
    if not exp_date:
        errors.append("Date is required.")
    else:
        try:
            datetime.strptime(exp_date, "%Y-%m-%d")
        except ValueError:
            errors.append("Invalid date format.")

    cleaned = {
        "title": title,
        "amount_p": amount_p,
        "category": category,
        "expense_date": exp_date,
        "notes": notes,
        "payment_method": pay if pay in PAYMENT_METHODS else "UPI",
    }
    return errors, cleaned


def month_total_p(db, month_str):
    """Total paise spent in a YYYY-MM month."""
    row = db.execute(
        "SELECT COALESCE(SUM(amount_p), 0) AS total FROM expenses WHERE expense_date LIKE ?",
        (f"{month_str}%",),
    ).fetchone()
    return row["total"]


def build_expense_filters(args):
    """Shared WHERE-clause builder for /expenses and /export.

    Returns (where_sql, params, sel_month, sel_cat, sel_pay, query_text).
    """
    sel_month = args.get("month", "").strip()
    sel_cat   = args.get("category", "").strip()
    sel_pay   = args.get("pay", "").strip()
    query     = args.get("q", "").strip()

    where  = "WHERE 1=1"
    params = []
    if sel_month:
        where += " AND expense_date LIKE ?"
        params.append(f"{sel_month}%")
    if sel_cat:
        where += " AND category = ?"
        params.append(sel_cat)
    if sel_pay:
        where += " AND payment_method = ?"
        params.append(sel_pay)
    if query:
        where += " AND (title LIKE ? OR notes LIKE ?)"
        params.extend([f"%{query}%", f"%{query}%"])

    return where, params, sel_month, sel_cat, sel_pay, query


# Expose helpers to templates
app.jinja_env.globals["fmt_inr"] = fmt_inr
app.jinja_env.globals["categories"] = CATEGORIES
app.jinja_env.globals["payment_methods"] = PAYMENT_METHODS


# ---------------------------------------------------------------------------
# Route: Dashboard (index)
# ---------------------------------------------------------------------------

@app.route("/")
def index():
    db = get_db()

    today = date.today()
    month_str = today.strftime("%Y-%m")
    days_in_month = calendar.monthrange(today.year, today.month)[1]
    days_elapsed  = today.day
    days_left     = days_in_month - days_elapsed

    total_month_p = month_total_p(db, month_str)
    budget_p = db.execute("SELECT monthly_p FROM budget WHERE id=1").fetchone()["monthly_p"]
    remaining_p = budget_p - total_month_p

    # Spending by category (this month)
    cat_rows = [
        {"category": r["category"], "total": r["total"]}
        for r in db.execute(
            """SELECT category, COALESCE(SUM(amount_p),0) AS total
               FROM expenses
               WHERE expense_date LIKE ?
               GROUP BY category
               ORDER BY total DESC""",
            (f"{month_str}%",),
        ).fetchall()
    ]

    # --- Insights ---------------------------------------------------------
    insights = None
    if total_month_p > 0 and cat_rows:
        top = cat_rows[0]
        daily_avg_p   = total_month_p // days_elapsed
        projected_p   = daily_avg_p * days_in_month
        insights = {
            "top_category": top["category"],
            "top_share": round(top["total"] / total_month_p * 100),
            "daily_avg_p": daily_avg_p,
            "projected_p": projected_p,
            "days_left": days_left,
            "projected_over_p": projected_p - budget_p if budget_p > 0 else 0,
        }

    # --- 6-month spending trend -------------------------------------------
    trend_labels, trend_totals = [], []
    y, m = today.year, today.month
    for _ in range(6):
        key = f"{y:04d}-{m:02d}"
        trend_labels.append(date(y, m, 1).strftime("%b"))
        trend_totals.append(month_total_p(db, key))
        m -= 1
        if m == 0:
            m, y = 12, y - 1
    trend_labels.reverse()
    trend_totals.reverse()

    # --- Per-category budget progress (this month) -------------------------
    cat_budgets = []
    for r in db.execute(
        """SELECT cb.category, cb.monthly_p AS budget_p,
                  COALESCE(SUM(e.amount_p), 0) AS spent_p
           FROM category_budgets cb
           LEFT JOIN expenses e
             ON e.category = cb.category AND e.expense_date LIKE ?
           GROUP BY cb.category
           HAVING cb.monthly_p > 0
           ORDER BY spent_p DESC""",
        (f"{month_str}%",),
    ).fetchall():
        pct = min(int(r["spent_p"] / r["budget_p"] * 100), 100) if r["budget_p"] else 0
        cat_budgets.append({
            "category": r["category"],
            "budget_p": r["budget_p"],
            "spent_p": r["spent_p"],
            "pct": pct,
        })

    # Recent 5 transactions (all time, newest first)
    recent = [
        dict(r) for r in db.execute(
            """SELECT * FROM expenses ORDER BY expense_date DESC, id DESC LIMIT 5"""
        ).fetchall()
    ]

    return render_template(
        "index.html",
        total_month_p=total_month_p,
        budget_p=budget_p,
        remaining_p=remaining_p,
        cat_rows=cat_rows,
        recent=recent,
        month_label=today.strftime("%B %Y"),
        insights=insights,
        trend_labels=trend_labels,
        trend_totals=trend_totals,
        cat_budgets=cat_budgets,
    )


# ---------------------------------------------------------------------------
# Route: Expenses list (history) — with search, filters, pagination
# ---------------------------------------------------------------------------

@app.route("/expenses")
def expenses():
    db = get_db()

    where, params, sel_month, sel_cat, sel_pay, query = build_expense_filters(request.args)

    try:
        page = max(int(request.args.get("page", 1)), 1)
    except (TypeError, ValueError):
        page = 1

    total_count = db.execute(
        f"SELECT COUNT(*) AS c FROM expenses {where}", params
    ).fetchone()["c"]
    total_pages = max((total_count + EXPENSES_PER_PAGE - 1) // EXPENSES_PER_PAGE, 1)
    page = min(page, total_pages)
    offset = (page - 1) * EXPENSES_PER_PAGE

    rows = [
        dict(r) for r in db.execute(
            f"SELECT * FROM expenses {where} ORDER BY expense_date DESC, id DESC"
            f" LIMIT {EXPENSES_PER_PAGE} OFFSET {offset}",
            params,
        ).fetchall()
    ]

    # Total for the filtered view (all pages, not just this one)
    total_p = db.execute(
        f"SELECT COALESCE(SUM(amount_p),0) AS t FROM expenses {where}", params
    ).fetchone()["t"]

    months = db.execute(
        "SELECT DISTINCT substr(expense_date,1,7) AS m FROM expenses ORDER BY m DESC"
    ).fetchall()

    # Preserve filters when building pagination links
    base_args = {k: v for k, v in request.args.items() if k != "page" and v}

    return render_template(
        "expenses.html",
        rows=rows,
        total_p=total_p,
        months=[r["m"] for r in months],
        sel_month=sel_month,
        sel_cat=sel_cat,
        sel_pay=sel_pay,
        query=query,
        page=page,
        total_pages=total_pages,
        total_count=total_count,
        base_args=base_args,
    )


# ---------------------------------------------------------------------------
# Route: CSV export (respects the same filters as /expenses)
# ---------------------------------------------------------------------------

@app.route("/export")
def export_csv():
    db = get_db()
    where, params, *_ = build_expense_filters(request.args)

    rows = db.execute(
        f"SELECT expense_date, title, category, payment_method, amount_p, notes"
        f" FROM expenses {where} ORDER BY expense_date DESC, id DESC",
        params,
    ).fetchall()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Date", "Title", "Category", "Payment Method", "Amount (INR)", "Notes"])
    for r in rows:
        writer.writerow([
            r["expense_date"], r["title"], r["category"],
            r["payment_method"] or "", f"{r['amount_p'] / 100:.2f}", r["notes"] or "",
        ])

    resp = Response(output.getvalue(), mimetype="text/csv")
    resp.headers["Content-Disposition"] = "attachment; filename=spendwise-expenses.csv"
    return resp


# ---------------------------------------------------------------------------
# Route: Add expense
# ---------------------------------------------------------------------------

@app.route("/add", methods=["GET", "POST"])
def add_expense():
    if request.method == "POST":
        errors, cleaned = validate_expense_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "add_expense.html",
                form_data=request.form,
                page_title="Add Expense",
            )

        get_db().execute(
            "INSERT INTO expenses (title, amount_p, category, expense_date, notes, payment_method)"
            " VALUES (?,?,?,?,?,?)",
            (cleaned["title"], cleaned["amount_p"], cleaned["category"],
             cleaned["expense_date"], cleaned["notes"], cleaned["payment_method"]),
        )
        get_db().commit()
        flash("Expense added successfully!", "success")
        return redirect(url_for("index"))

    # GET – prefill today's date
    return render_template(
        "add_expense.html",
        form_data={"expense_date": date.today().isoformat()},
        page_title="Add Expense",
    )


# ---------------------------------------------------------------------------
# Route: Edit expense
# ---------------------------------------------------------------------------

@app.route("/edit/<int:expense_id>", methods=["GET", "POST"])
def edit_expense(expense_id):
    db = get_db()
    expense = db.execute("SELECT * FROM expenses WHERE id=?", (expense_id,)).fetchone()

    if expense is None:
        flash("Expense not found.", "error")
        return redirect(url_for("expenses"))

    if request.method == "POST":
        errors, cleaned = validate_expense_form(request.form)
        if errors:
            for e in errors:
                flash(e, "error")
            return render_template(
                "add_expense.html",
                form_data=request.form,
                page_title="Edit Expense",
                expense_id=expense_id,
            )

        db.execute(
            """UPDATE expenses
               SET title=?, amount_p=?, category=?, expense_date=?, notes=?, payment_method=?
               WHERE id=?""",
            (cleaned["title"], cleaned["amount_p"], cleaned["category"],
             cleaned["expense_date"], cleaned["notes"], cleaned["payment_method"],
             expense_id),
        )
        db.commit()
        flash("Expense updated successfully!", "success")
        return redirect(url_for("expenses"))

    # GET – fill form with existing values
    form_data = {
        "title":          expense["title"],
        "amount":         f"{paise_to_inr(expense['amount_p']):.2f}",
        "category":       expense["category"],
        "expense_date":   expense["expense_date"],
        "notes":          expense["notes"],
        "payment_method": expense["payment_method"] or "UPI",
    }
    return render_template(
        "add_expense.html",
        form_data=form_data,
        page_title="Edit Expense",
        expense_id=expense_id,
    )


# ---------------------------------------------------------------------------
# Route: Delete expense
# ---------------------------------------------------------------------------

@app.route("/delete/<int:expense_id>", methods=["POST"])
def delete_expense(expense_id):
    db = get_db()
    expense = db.execute("SELECT id FROM expenses WHERE id=?", (expense_id,)).fetchone()
    if expense is None:
        flash("Expense not found.", "error")
    else:
        db.execute("DELETE FROM expenses WHERE id=?", (expense_id,))
        db.commit()
        flash("Expense deleted.", "success")
    return redirect(url_for("expenses"))


# ---------------------------------------------------------------------------
# Route: Budget (global + per-category)
# ---------------------------------------------------------------------------

@app.route("/budget", methods=["GET", "POST"])
def budget():
    db = get_db()

    if request.method == "POST":
        # --- Global monthly budget ---
        amount_s = request.form.get("budget_amount", "").strip()
        if amount_s:
            try:
                amount_f = float(amount_s)
                if amount_f < 0:
                    raise ValueError
                db.execute(
                    "UPDATE budget SET monthly_p=? WHERE id=1",
                    (inr_to_paise(amount_s),),
                )
            except (ValueError, TypeError):
                flash("Please enter a valid positive budget amount.", "error")
                return redirect(url_for("budget"))

        # --- Per-category budgets (fields named catbudget_<index>) ---
        for i, cat in enumerate(CATEGORIES):
            val = request.form.get(f"catbudget_{i}", "").strip()
            if val == "":
                continue  # leave existing value untouched
            try:
                amount_f = float(val)
                if amount_f < 0:
                    raise ValueError
                db.execute(
                    """INSERT INTO category_budgets (category, monthly_p)
                       VALUES (?, ?)
                       ON CONFLICT(category) DO UPDATE SET monthly_p=excluded.monthly_p""",
                    (cat, inr_to_paise(val)),
                )
            except (ValueError, TypeError):
                flash(f"Invalid budget amount for '{cat}' — skipped.", "error")

        db.commit()
        flash("Budgets updated!", "success")
        return redirect(url_for("budget"))

    # GET
    budget_p = db.execute("SELECT monthly_p FROM budget WHERE id=1").fetchone()["monthly_p"]

    today      = date.today()
    month_str  = today.strftime("%Y-%m")
    spent_p    = month_total_p(db, month_str)
    remaining_p = budget_p - spent_p

    saved = {r["category"]: r["monthly_p"]
             for r in db.execute("SELECT category, monthly_p FROM category_budgets").fetchall()}
    cat_budget_rows = [
        {"category": cat,
         "budget_p": saved.get(cat, 0),
         "spent_p": db.execute(
             "SELECT COALESCE(SUM(amount_p),0) AS s FROM expenses"
             " WHERE category=? AND expense_date LIKE ?",
             (cat, f"{month_str}%")).fetchone()["s"]}
        for cat in CATEGORIES
    ]

    return render_template(
        "budget.html",
        budget_p=budget_p,
        spent_p=spent_p,
        remaining_p=remaining_p,
        month_label=today.strftime("%B %Y"),
        cat_budget_rows=cat_budget_rows,
    )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
