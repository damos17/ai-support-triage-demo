from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from .models import MessageIn
from .services import SupportWorkflow

app = FastAPI(title="AI Support Triage Demo", version="0.1.0")
workflow = SupportWorkflow()


@app.get("/health")
def health():
    return {"status": "ok", "llm_mode": "mock"}


@app.post("/api/messages")
def process_message(message: MessageIn):
    return workflow.process(message.customer_id, message.text)


@app.get("/api/cases")
def cases():
    return [c.model_dump(mode="json") for c in workflow.cases]


@app.get("/api/incidents")
def incidents():
    return [i.model_dump(mode="json") for i in workflow.incidents]


@app.post("/api/tickets/{case_id}/approve")
def approve_ticket(case_id: str):
    if case_id not in workflow.tickets:
        raise HTTPException(status_code=404, detail="Ticket draft not found")
    return workflow.approve(case_id).model_dump(mode="json")


@app.get("/", response_class=HTMLResponse)
def dashboard():
    return """<!doctype html><html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width'>
<title>AI Support Triage</title><style>
body{font-family:Inter,system-ui,sans-serif;background:#0b1020;color:#e8ecf5;margin:0}.wrap{max-width:1100px;margin:40px auto;padding:0 20px}
.card{background:#141b2d;border:1px solid #26304a;border-radius:16px;padding:20px;margin:16px 0}h1{font-size:32px}h2{font-size:18px;color:#aeb9d4}
textarea,input{box-sizing:border-box;width:100%;background:#0d1425;color:#fff;border:1px solid #34405e;border-radius:10px;padding:12px;margin:6px 0 12px}
button{background:#fff;color:#111827;border:0;border-radius:10px;padding:11px 16px;font-weight:700;cursor:pointer}.muted{color:#8995b3}.grid{display:grid;grid-template-columns:1fr 1fr;gap:16px}pre{white-space:pre-wrap;word-break:break-word;color:#b8f7cf}@media(max-width:760px){.grid{grid-template-columns:1fr}}
</style></head><body><div class='wrap'><p class='muted'>PUBLIC · SYNTHETIC DATA · MOCK LLM</p><h1>AI Support Triage Agent</h1>
<p class='muted'>Issue detection → case creation → knowledge lookup → escalation → incident correlation → human approval.</p>
<div class='grid'><div class='card'><h2>Message simulator</h2><label>Customer</label><input id='customer' value='northstar-labs'><label>Message</label>
<textarea id='message' rows='7'>Since this morning our data imports are failing with timeout errors.</textarea><button onclick='send()'>Process message</button></div>
<div class='card'><h2>Pipeline result</h2><pre id='result'>Send a synthetic message to start.</pre></div></div>
<div class='card'><h2>Try an incident</h2><p class='muted'>Send similar data/import failures from three different customer IDs. The third case will trigger a potential incident.</p></div>
<script>async function send(){let r=await fetch('/api/messages',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({customer_id:customer.value,text:message.value})});let d=await r.json();result.textContent=JSON.stringify(d,null,2);if(d.ticket){let b=document.createElement('button');b.textContent='Approve mock ticket';b.onclick=async()=>{let x=await fetch('/api/tickets/'+d.case.case_id+'/approve',{method:'POST'});result.textContent=JSON.stringify({...d,approved_ticket:await x.json()},null,2)};result.appendChild(document.createElement('br'));result.appendChild(b)}}</script>
</div></body></html>"""
