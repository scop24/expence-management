# SpendWise – Student Expense Tracker 💰

A clean, professional expense tracker built for students to manage their monthly budgets. Built with Python Flask, SQLite, and vanilla CSS/JS — no external APIs, no complicated frameworks.

---

## ✨ Features

| Feature | Details |
|---|---|
| **Dashboard** | Monthly spending summary, budget progress bar, category donut chart, recent transactions |
| **Add Expense** | Title, amount (₹), category, date, optional notes — fully validated |
| **Edit Expense** | Pre-fills the form with existing values |
| **Delete Expense** | Confirmation dialog before deleting |
| **Transaction History** | Filter by month, category, and payment method; **text search** across titles/notes; **pagination** (15/page); shows filtered total |
| **Budget Management** | Set a global monthly budget **plus per-category budgets**; warns when exceeded or low |
| **CSV Export** | Download filtered expenses as CSV from the History page |
| **Smart Insights** | Auto-generated: top category share, daily average, projected month-end total, budget trajectory |
| **Spending Trend** | 6-month bar chart on the dashboard |
| **Payment Method** | Track UPI / Cash / Card / Net Banking per expense, with filtering |
| **Dark Mode** | Toggle in the sidebar, persisted in localStorage, no flash on load |
| **INR Formatting** | Proper Indian number formatting (e.g. ₹1,23,456.00) |
| **Demo Data** | 8 sample expenses + ₹3,000 budget auto-seeded on first run |
| **Persistent Storage** | SQLite database (`spendwise.db`) survives server restarts |

---

## 🚀 Setup & Run

### Prerequisites
- Python 3.8 or newer
- pip

### 1 — Clone / open the folder

```bash
cd "student expence"
```

### 2 — Create a virtual environment (recommended)

```bash
python -m venv .venv

# Windows PowerShell
.venv\Scripts\Activate.ps1

# macOS / Linux
source .venv/bin/activate
```

### 3 — Install Flask

```bash
pip install -r requirements.txt
```

### 4 — Run the app

```bash
python app.py
```

Open your browser at **http://127.0.0.1:5000**

---

## 🗄️ Database

- File: `spendwise.db` (auto-created in the project root on first run)
- Tables: `expenses`, `budget`
- Money is stored as **integer paise** (₹1 = 100 paise) to avoid floating-point errors

### Reset to clean state (remove demo data)

```bash
# Stop the server first, then:
del spendwise.db        # Windows
rm spendwise.db         # macOS / Linux
# Restart: python app.py
```

---

## 📁 Project Structure

```
student expence/
├── app.py               ← Flask app + all routes + DB logic
├── spendwise.db         ← SQLite database (auto-created)
├── requirements.txt     ← Only needs Flask
├── README.md
├── .gitignore
├── templates/
│   ├── base.html        ← Shared layout (sidebar, flash messages)
│   ├── index.html       ← Dashboard
│   ├── expenses.html    ← Transaction history + filters
│   ├── add_expense.html ← Add and Edit form (shared)
│   └── budget.html      ← Budget management
└── static/
    ├── style.css        ← Full custom CSS design system
    └── script.js        ← Sidebar toggle, pie chart, delete confirm
```

---

## 💡 Implementation Decisions

| Decision | Reason |
|---|---|
| **Paise (integer) for money** | Eliminates floating-point rounding errors (e.g. 0.1 + 0.2 ≠ 0.3) |
| **Single `add_expense.html` for add & edit** | Reduces duplication; the form re-uses the same Jinja template |
| **Single `validate_expense_form()`** | Add & edit share one validation path — no duplicated logic |
| **Secret key from environment** | `SECRET_KEY` env var; hardcoded key removed |
| **Auto-migration** | `ensure_schema()` upgrades older databases in place |
| **Parameterized SQL queries** | Prevents SQL injection attacks |
| **`sqlite3.Row` row factory** | Lets us access DB columns by name (`row['title']`) instead of index |
| **WAL journal mode** | Better concurrency if multiple tabs are open simultaneously |
| **Vanilla Canvas API for chart** | Zero external dependencies; works offline |

---

## ⚠️ Known Limitations

1. **Single user** — No authentication; suitable for personal local use only.
2. **No multi-currency** — INR only.

## 🔄 Upgrading from an older version

Just replace the project files and restart — the app auto-migrates your existing
`spendwise.db` on first run (adds the `payment_method` column and the
`category_budgets` table). Your data is preserved.

---

## 🛠️ Development

To run in debug mode (auto-reloads on code changes):

```bash
python app.py
# Flask runs with debug=True by default in this MVP
```

Change the `secret_key` in `app.py` before any production deployment.
