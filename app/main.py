import json
import os
from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, Response
from fastapi.templating import Jinja2Templates

from .models import MessageIn
from .workflow import SupportWorkflow

app = FastAPI(title="AI Support Triage Demo", version="0.2.0")
templates = Jinja2Templates(directory="app/templates")
workflow = SupportWorkflow()

FAVICON_SVG = """<svg xmlns=\"http://www.w3.org/2000/svg\" viewBox=\"0 0 64 64\">
<rect width=\"64\" height=\"64\" rx=\"14\" fill=\"#111b2e\"/>
<path d=\"M18 18h28v8H26v8h16v8H26v12h-8V18Z\" fill=\"#8ab4ff\"/>
<circle cx=\"46\" cy=\"46\" r=\"7\" fill=\"#5ee38d\"/>
</svg>"""


@app.get("/health")
def health():
    return {"status": "ok", "llm_mode": os.getenv("LLM_MODE", "mock"), "version": "0.2.0"}


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return Response(content=FAVICON_SVG, media_type="image/svg+xml")


@app.post("/api/messages")
async def process_message(message: MessageIn):
    return await workflow.process(message.customer_id, message.text)


@app.get("/api/cases")
def cases():
    return [c.model_dump(mode="json") for c in workflow.cases]


@app.get("/api/incidents")
def incidents():
    return [i.model_dump(mode="json") for i in workflow.incidents]


@app.get("/api/stats")
def stats():
    return workflow.stats()


@app.get("/api/scenarios")
def scenarios():
    path = Path("data/scenarios.json")
    return json.loads(path.read_text(encoding="utf-8"))


@app.post("/api/tickets/{case_id}/approve")
def approve_ticket(case_id: str):
    if case_id not in workflow.tickets:
        raise HTTPException(status_code=404, detail="Ticket draft not found")
    return workflow.approve(case_id).model_dump(mode="json")


@app.post("/api/reset")
def reset_demo():
    workflow.reset()
    return {"status": "reset"}


@app.get("/", response_class=HTMLResponse)
def dashboard(request: Request):
    return templates.TemplateResponse(request=request, name="dashboard.html")
