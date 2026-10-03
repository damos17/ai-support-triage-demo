import json
import os
import re
import secrets
import time
from collections import OrderedDict
from pathlib import Path
from threading import Lock

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles

from .evaluation import run_evaluation
from .models import MessageIn
from .db import MemoryStore
from .safety import escape_dynamic_text
from .workflow import SupportWorkflow

app = FastAPI(title="AI Support Triage Demo", version="0.6.0")
workflow = SupportWorkflow()

# Public deployments: DEMO_SESSIONS=1 gives every visitor a private in-memory state
# (own cases, counters, incidents), identified by a random cookie. Default: one shared state.
DEMO_SESSIONS = os.getenv("DEMO_SESSIONS", "").strip() in {"1", "true", "yes"}
SESSION_COOKIE = "triage_sid"
SESSION_TTL = int(os.getenv("DEMO_SESSION_TTL", "7200"))
SESSION_MAX = int(os.getenv("DEMO_MAX_SESSIONS", "500"))
_SID_RE = re.compile(r"^[A-Za-z0-9_-]{20,64}$")
_sessions: "OrderedDict[str, tuple[float, SupportWorkflow]]" = OrderedDict()
_sessions_lock = Lock()


def _session_workflow(sid: str) -> SupportWorkflow:
    now = time.time()
    with _sessions_lock:
        entry = _sessions.pop(sid, None)
        # oldest sessions first: drop the expired ones and anything over the limit
        while _sessions and (len(_sessions) >= SESSION_MAX or next(iter(_sessions.values()))[0] < now - SESSION_TTL):
            _sessions.popitem(last=False)
        if entry and entry[0] >= now - SESSION_TTL:
            flow = entry[1]
        else:
            flow = SupportWorkflow(store=MemoryStore(), provider=workflow.llm)
        _sessions[sid] = (now, flow)
        return flow


def wf(request: Request) -> SupportWorkflow:
    """The workflow this request works with: the visitor's own one in session mode."""
    if not DEMO_SESSIONS:
        return workflow
    return _session_workflow(request.state.sid)

# Optional visual theme for embedding the demo into another site (e.g. DEMO_THEME=damos).
DEMO_THEME = os.getenv("DEMO_THEME", "").strip()
THEME_DIR = Path("app/theme")
if DEMO_THEME and (THEME_DIR / f"{DEMO_THEME}.css").is_file():
    app.mount("/theme", StaticFiles(directory=THEME_DIR), name="theme")
else:
    DEMO_THEME = ""

# Space-separated origins allowed to embed the dashboard in an iframe. Default: nobody.
FRAME_ANCESTORS = os.getenv("FRAME_ANCESTORS", "").strip() or "'none'"

FAVICON_SVG = """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 64 64\">
<rect width=\"64\" height=\"64\" rx=\"14\" fill=\"#111b2e\"/>
<path d=\"M18 18h28v8H26v8h16v8H26v12h-8V18Z\" fill=\"#8ab4ff\"/>
<circle cx=\"46\" cy=\"46\" r=\"7\" fill=\"#5ee38d\"/>
</svg>"""


def safe(payload):
    return escape_dynamic_text(payload)


@app.middleware("http")
async def add_security_headers(request: Request, call_next):
    new_sid = None
    if DEMO_SESSIONS:
        sid = request.cookies.get(SESSION_COOKIE, "")
        if not _SID_RE.match(sid):
            sid = new_sid = secrets.token_urlsafe(24)
        request.state.sid = sid
    response = await call_next(request)
    if new_sid:
        secure = request.headers.get("x-forwarded-proto", request.url.scheme) == "https"
        response.set_cookie(SESSION_COOKIE, new_sid, max_age=SESSION_TTL, httponly=True, samesite="lax", secure=secure)
    response.headers["X-Content-Type-Options"] = "nosniff"
    if FRAME_ANCESTORS == "'none'":
        response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
    response.headers["Content-Security-Policy"] = (
        "default-src 'self'; object-src 'none'; base-uri 'none'; "
        f"frame-ancestors {FRAME_ANCESTORS}; font-src 'self'; "
        "img-src 'self' data:; connect-src 'self'; style-src 'self' 'unsafe-inline'; "
        "script-src 'self' 'unsafe-inline'"
    )
    return response


@app.get("/health")
def health():
    return {"status": "ok", "llm_mode": os.getenv("LLM_MODE", "mock"), "version": "0.6.0"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


@app.post("/api/messages")
async def process_message(message: MessageIn, request: Request):
    return safe(await wf(request).process(message.customer_id, message.text))


@app.get("/api/cases")
def cases(
    request: Request,
    status: str | None = Query(default=None, max_length=40),
    category: str | None = Query(default=None, max_length=60),
    limit: int = Query(default=50, ge=1, le=200),
):
    items = wf(request).cases
    if status:
        items = [case for case in items if case.status == status]
    if category:
        items = [case for case in items if case.category.value == category]
    items = sorted(items, key=lambda case: case.created_at, reverse=True)[:limit]
    return safe([case.model_dump(mode="json") for case in items])


@app.get("/api/cases/{case_id}")
def case_detail(case_id: str, request: Request):
    detail = wf(request).case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
    return safe(detail)


@app.get("/api/incidents")
def incidents(request: Request):
    return safe([incident.model_dump(mode="json") for incident in wf(request).incidents])


@app.get("/api/audit")
def audit(request: Request, limit: int = Query(default=50, ge=1, le=200)):
    return safe(wf(request).audit(limit=limit))


@app.get("/api/telemetry")
def telemetry(request: Request):
    return safe(wf(request).telemetry())


@app.get("/api/evaluation")
async def evaluation():
    return safe(await run_evaluation(workflow.llm))


@app.get("/api/stats")
def stats(request: Request):
    return wf(request).stats()


@app.get("/api/scenarios")
def scenarios():
    path = Path("data/scenarios.json")
    return safe(json.loads(path.read_text(encoding="utf-8")))


@app.post("/api/tickets/{case_id}/approve")
def approve_ticket(case_id: str, request: Request):
    current = wf(request)
    if case_id not in current.tickets:
        raise HTTPException(status_code=404, detail="Ticket draft not found")
    return safe(current.approve(case_id).model_dump(mode="json"))


@app.post("/api/reset")
def reset_demo(request: Request):
    wf(request).reset()
    return {"status": "reset"}


@app.get("/", response_class=HTMLResponse)
def dashboard():
    html = Path("app/templates/dashboard.html").read_text(encoding="utf-8").replace("v0.5", "v0.6")
    if DEMO_THEME:
        html = html.replace('<html lang="en">', f'<html lang="en" class="theme-{DEMO_THEME}">', 1)
        html = html.replace(
            "</head>",
            f'<link rel="stylesheet" href="/theme/{DEMO_THEME}.css">\n'
            "<script>try{if(!localStorage.getItem('triage_lang'))localStorage.setItem('triage_lang','ru')}catch(e){}</script>\n"
            "</head>",
            1,
        )
    return HTMLResponse(html)
