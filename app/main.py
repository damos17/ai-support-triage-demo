import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from .evaluation import run_evaluation
from .models import MessageIn
from .safety import escape_dynamic_text
from .workflow import SupportWorkflow

app = FastAPI(title="AI Support Triage Demo", version="0.6.0")
templates = Jinja2Templates(directory="app/templates")
workflow = SupportWorkflow()

FAVICON_SVG = """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 64 64\">
<rect width=\"64\" height=\"64\" rx=\"14\" fill=\"#111b2e\"/>
<path d=\"M18 18h28v8H26v8h16v8H26v12h-8V18Z\" fill=\"#8ab4ff\"/>
<circle cx=\"46\" cy=\"46\" r=\"7\" fill=\"#5ee38d\"/>
</svg>"""


def safe(payload):
    return escape_dynamic_text(payload)


@app.get("/health")
def health():
    return {"status": "ok", "llm_mode": os.getenv("LLM_MODE", "mock"), "version": "0.6.0"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


@app.post("/api/messages")
async def process_message(message: MessageIn):
    return safe(await workflow.process(message.customer_id, message.text))


@app.get("/api/cases")
def cases(
    status: str | None = Query(default=None, max_length=40),
    category: str | None = Query(default=None, max_length=60),
    limit: int = Query(default=50, ge=1, le=200),
):
    items = workflow.cases
    if status:
        items = [case for case in items if case.status == status]
    if category:
        items = [case for case in items if case.category.value == category]
    items = sorted(items, key=lambda case: case.created_at, reverse=True)[:limit]
    return safe([case.model_dump(mode="json") for case in items])


@app.get("/api/cases/{case_id}")
def case_detail(case_id: str):
    detail = workflow.case_detail(case_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Case not found")
    return safe(detail)


@app.get("/api/incidents")
def incidents():
    return safe([incident.model_dump(mode="json") for incident in workflow.incidents])


@app.get("/api/audit")
def audit(limit: int = Query(default=50, ge=1, le=200)):
    return safe(workflow.audit(limit=limit))


@app.get("/api/telemetry")
def telemetry():
    return safe(workflow.telemetry())


@app.get("/api/evaluation")
async def evaluation():
    return safe(await run_evaluation(workflow.llm))


@app.get("/api/stats")
def stats():
    return workflow.stats()


@app.get("/api/scenarios")
def scenarios():
    path = Path("data/scenarios.json")
    return safe(json.loads(path.read_text(encoding="utf-8")))


@app.post("/api/tickets/{case_id}/approve")
def approve_ticket(case_id: str):
    if case_id not in workflow.tickets:
        raise HTTPException(status_code=404, detail="Ticket draft not found")
    return safe(workflow.approve(case_id).model_dump(mode="json"))


@app.post("/api/reset")
def reset_demo():
    workflow.reset()
    return {"status": "reset"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")
