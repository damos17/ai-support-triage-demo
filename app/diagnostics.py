"""Synthetic diagnostics: log search and a read-only SQL check for escalated cases.

Everything here is fictional demo data. The agent picks a plan by category, searches
the service logs, runs one read-only query against a small in-memory database and
returns what it found, so a reviewer can see *why* a ticket goes to engineering.
"""

import sqlite3
from contextlib import closing
from dataclasses import dataclass

from .models import Category

# Fictional service logs for the morning of the demo incident.
LOGS = [
    ("06:11:58", "ingest-worker", "INFO", "import started source=marketplace customer=northstar-labs"),
    ("06:12:41", "ingest-worker", "ERROR", "import failed source=marketplace customer=northstar-labs: upstream timeout after 30s"),
    ("06:14:03", "ingest-worker", "ERROR", "import failed source=marketplace customer=vertex-retail: upstream timeout after 30s"),
    ("06:15:22", "ingest-worker", "WARN", "retry 3/3 source=marketplace customer=orbit-commerce"),
    ("06:15:52", "ingest-worker", "ERROR", "import failed source=marketplace customer=orbit-commerce: upstream timeout after 30s"),
    ("06:16:10", "ingest-worker", "INFO", "import finished source=ads customer=ember-media rows=1840"),
    ("07:02:11", "payments", "WARN", "gateway timeout invoice=INV-2291 customer=vertex-retail, retrying charge"),
    ("07:02:44", "payments", "INFO", "charge succeeded invoice=INV-2291 customer=vertex-retail amount=4900"),
    ("07:02:46", "payments", "INFO", "charge succeeded invoice=INV-2291 customer=vertex-retail amount=4900"),
    ("07:03:01", "mailer", "ERROR", "invoice email deferred invoice=INV-2291: SMTP 451 try again later"),
    ("08:30:05", "identity", "ERROR", "SSO login rejected customer=atlas-studio: signing certificate expired 2026-10-03"),
    ("08:31:40", "identity", "ERROR", "SSO login rejected customer=atlas-studio: signing certificate expired 2026-10-03"),
    ("08:32:12", "identity", "INFO", "password login ok customer=ember-media"),
]

SCHEMA = """
CREATE TABLE imports (customer_id TEXT, source TEXT, started_at TEXT, status TEXT, error TEXT);
CREATE TABLE payments (customer_id TEXT, invoice_id TEXT, amount INTEGER, charged_at TEXT, status TEXT);
CREATE TABLE logins (customer_id TEXT, method TEXT, at TEXT, result TEXT);
"""
ROWS = {
    "imports": [
        ("northstar-labs", "marketplace", "2026-10-04 05:10", "ok", None),
        ("northstar-labs", "marketplace", "2026-10-04 06:12", "failed", "upstream timeout"),
        ("vertex-retail", "marketplace", "2026-10-04 06:14", "failed", "upstream timeout"),
        ("orbit-commerce", "marketplace", "2026-10-04 06:15", "failed", "upstream timeout"),
        ("orbit-commerce", "marketplace", "2026-10-04 06:31", "failed", "upstream timeout"),
        ("ember-media", "ads", "2026-10-04 06:16", "ok", None),
    ],
    "payments": [
        ("vertex-retail", "INV-2244", 4900, "2026-09-04 07:01", "succeeded"),
        ("vertex-retail", "INV-2291", 4900, "2026-10-04 07:02", "succeeded"),
        ("vertex-retail", "INV-2291", 4900, "2026-10-04 07:02", "succeeded"),
        ("orbit-commerce", "INV-2290", 2900, "2026-10-04 06:58", "succeeded"),
    ],
    "logins": [
        ("atlas-studio", "sso", "2026-10-04 08:30", "rejected"),
        ("atlas-studio", "sso", "2026-10-04 08:31", "rejected"),
        ("atlas-studio", "password", "2026-10-03 18:20", "ok"),
        ("ember-media", "password", "2026-10-04 08:32", "ok"),
    ],
}


@dataclass(frozen=True)
class Plan:
    services: tuple[str, ...]  # logs the agent reads
    log_filter: str            # substring the agent searches for in them
    sql: str                 # read-only query, parameters as ?
    finding_en: str
    finding_ru: str


PLANS = {
    Category.data_ingestion: Plan(
        services=("ingest-worker",),
        log_filter="import failed",
        sql=(
            "SELECT customer_id, COUNT(*) AS failed, MAX(started_at) AS last_failure\n"
            "FROM imports\n"
            "WHERE status = 'failed' AND started_at >= ?\n"
            "GROUP BY customer_id\n"
            "ORDER BY failed DESC"
        ),
        finding_en="Marketplace imports time out since 06:12 for several customers: the source is down, not one account.",
        finding_ru="С 06:12 импорт из маркетплейса падает по тайм-ауту у нескольких клиентов: проблема в источнике, а не в одном аккаунте.",
    ),
    Category.billing: Plan(
        services=("payments", "mailer"),
        log_filter="INV-2291",
        sql=(
            "SELECT invoice_id, COUNT(*) AS charges, SUM(amount) AS total\n"
            "FROM payments\n"
            "WHERE customer_id = ? AND status = 'succeeded'\n"
            "GROUP BY invoice_id\n"
            "HAVING COUNT(*) > 1"
        ),
        finding_en="Invoice INV-2291 was charged twice after a gateway timeout retry; the invoice email was deferred by SMTP.",
        finding_ru="Счёт INV-2291 списан дважды: после тайм-аута шлюза платёж повторился. Письмо со счётом не ушло из-за ошибки почтового сервера.",
    ),
    Category.authentication: Plan(
        services=("identity",),
        log_filter="SSO login rejected",
        sql=(
            "SELECT method, result, COUNT(*) AS attempts, MAX(at) AS last_attempt\n"
            "FROM logins\n"
            "WHERE customer_id = ? AND at >= ?\n"
            "GROUP BY method, result"
        ),
        finding_en="All SSO logins are rejected because the signing certificate expired on 2026-10-03; password login still works.",
        finding_ru="Вход через SSO отклоняется: 3 октября истёк сертификат подписи. Вход по паролю работает.",
    ),
}

# Demo customers each plan is written about; other customers fall back to these.
PLAN_CUSTOMER = {Category.billing: "vertex-retail", Category.authentication: "atlas-studio"}


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.executescript(SCHEMA)
    for table, rows in ROWS.items():
        marks = ",".join("?" * len(rows[0]))
        conn.executemany(f"INSERT INTO {table} VALUES ({marks})", rows)
    conn.execute("PRAGMA query_only = ON")
    return conn


def _params(category: Category, customer_id: str) -> tuple:
    customer = customer_id if category not in PLAN_CUSTOMER else PLAN_CUSTOMER[category]
    if category == Category.data_ingestion:
        return ("2026-10-04 06:00",)
    if category == Category.billing:
        return (customer,)
    return (customer, "2026-10-04 00:00")


def _render_sql(sql: str, params: tuple) -> str:
    """Query text as the agent shows it: parameters inlined as quoted literals."""
    out = sql
    for value in params:
        out = out.replace("?", "'" + str(value).replace("'", "''") + "'", 1)
    return out


def run(category: Category, customer_id: str) -> dict | None:
    plan = PLANS.get(category)
    if not plan:
        return None
    logs = [
        {"time": t, "service": s, "level": lvl, "message": m, "match": plan.log_filter in m}
        for t, s, lvl, m in LOGS
        if s in plan.services
    ]
    params = _params(category, customer_id)
    with closing(_connect()) as conn:
        cur = conn.execute(plan.sql, params)
        columns = [d[0] for d in cur.description]
        rows = [list(r) for r in cur.fetchall()]
    return {
        "log_query": plan.log_filter,
        "logs": logs,
        "sql": _render_sql(plan.sql, params),
        "columns": columns,
        "rows": rows,
        "finding": {"en": plan.finding_en, "ru": plan.finding_ru},
    }
