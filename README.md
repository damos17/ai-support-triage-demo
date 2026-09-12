# AI Support Triage Agent

[![tests](https://github.com/damos17/ai-support-triage-demo/actions/workflows/tests.yml/badge.svg)](https://github.com/damos17/ai-support-triage-demo/actions/workflows/tests.yml)

A runnable, privacy-safe demonstration of an **AI support operations workflow**: issue detection, structured case creation, knowledge retrieval, escalation, cross-customer incident correlation, ticket drafting, persistence, auditability, telemetry, and explicit human approval.

> **Public demo:** all customers, messages, rules, identifiers, and integrations are synthetic. This repository contains no production code or internal company data.

## What it demonstrates

```text
Incoming message
      ↓
LLM provider / deterministic mock
      ↓
Issue triage + severity
      ↓
Structured case
      ↓
Synthetic knowledge retrieval
      ↓
Decision: resolve / escalate
      ↓
Similarity-based incident correlation
      ↓
Ticket draft
      ↓
EXPLICIT HUMAN APPROVAL
      ↓
Mock external ticket ID
```

Every meaningful transition is also written to a persistent audit trail. Provider latency and token usage are captured at the triage boundary when available.

The point is not to build another chat interface. The project demonstrates how an LLM can sit inside a controlled, stateful workflow where the surrounding system owns persistence, observability, permissions and consequential actions.

## Quick start

### Python

```bash
git clone https://github.com/damos17/ai-support-triage-demo.git
cd ai-support-triage-demo
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Open `http://localhost:8000`.

The interactive API documentation is available at `http://localhost:8000/docs`.

### Docker

```bash
docker compose up --build
```

Docker is optional; the demo runs directly with Python.

## Operations dashboard

The bilingual EN/RU web UI includes:

- synthetic scenario presets;
- live workflow stages;
- case / severity / confidence output;
- knowledge-base guidance;
- potential incident alerts;
- explicit ticket approval controls;
- counters for cases, incidents, drafts and approved tickets;
- case-detail view;
- persistent audit trail;
- LLM provider / latency / token / known-cost telemetry;
- one-click three-customer incident demo;
- resettable demo state.

## Mock mode: zero cost

The default configuration is deterministic and requires no external service:

```env
LLM_MODE=mock
```

The mock understands the bundled English and Russian scenarios. It keeps the demo reproducible and makes CI deterministic.

## Optional real LLM mode

The workflow uses a provider interface rather than depending directly on one model vendor. An OpenAI-compatible endpoint can be enabled through environment variables:

```env
LLM_MODE=openai_compatible
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=...
LLM_MODEL=...
```

Only the triage boundary is exposed to the provider. Approval policy, persistence and ticket execution remain application responsibilities.

If the provider returns standard usage metadata, prompt/completion token counts are recorded. The demo deliberately does **not** invent a dollar cost for arbitrary compatible providers because pricing is provider- and model-specific.

## Persistence and auditability

Demo state is stored in SQLite under `data/demo.db` by default. Cases, ticket drafts, incidents and audit events survive an application restart.

Audit events cover the main workflow transitions, including:

- message received;
- triage completed;
- non-issue closed;
- case created;
- knowledge hit / miss;
- ticket drafted;
- potential incident detected;
- ticket explicitly approved.

The database is ignored by Git so public repository history never accumulates local demo state.

## Incident correlation

The current local correlator uses:

- issue category;
- independent synthetic customer IDs;
- token overlap between issue descriptions;
- a configurable minimum-customer threshold.

This is deliberately lightweight and explainable. It demonstrates the workflow boundary without pretending that simple lexical overlap is production-grade semantic similarity.

## Human-in-the-loop invariant

The central safety rule is:

```text
AI may prepare an action.
AI may not authorize that action.
```

A ticket can be drafted automatically, but a mock external ticket ID is created only after explicit approval.

## API

```text
GET  /health
POST /api/messages
GET  /api/cases
GET  /api/cases/{case_id}
GET  /api/incidents
GET  /api/audit
GET  /api/telemetry
GET  /api/stats
GET  /api/scenarios
POST /api/tickets/{case_id}/approve
POST /api/reset
```

## Project structure

```text
app/
├── main.py          FastAPI routes and UI entry point
├── workflow.py      orchestration, audit and state transitions
├── llm.py           provider interface + telemetry capture
├── db.py            SQLite persistence
├── knowledge.py     synthetic retrieval boundary
├── incidents.py     incident correlation
├── ticketing.py     draft + approval gate
├── models.py        domain + audit models
└── templates/       bilingual operations dashboard

data/
└── scenarios.json   synthetic demo scenarios

tests/
└── test_workflow.py workflow, safety, telemetry and persistence tests
```

## Tests

```bash
python -m pytest -q
```

The suite verifies that:

- conversational noise does not create a case;
- severe issues create ticket drafts;
- three related independent customers can trigger a potential incident;
- no external ticket is created before approval;
- approval is recorded in the audit trail;
- case-detail data includes related workflow state;
- telemetry aggregates provider calls;
- cases and audit events survive a restart.

GitHub Actions runs the tests and a FastAPI import smoke check on every push and pull request.

## Engineering decisions

**Mock-first, real-model optional.** The project can be evaluated without an API key, but the LLM boundary is explicit and replaceable.

**State belongs to the application.** The model does not own case history, incident state, ticket state or authorization.

**Observability is part of the workflow.** Audit events and provider telemetry are application data, not console-only diagnostics.

**Synthetic by construction.** No internal customer names, endpoints, credentials, prompts, production schemas, support conversations or proprietary business rules are included.

**Modular instead of monolithic.** Triage, persistence, retrieval, incident correlation and ticketing are separated so each boundary can evolve independently.

## Current version

**v0.3** adds a persistent audit trail, LLM telemetry, case-detail API/UI, bilingual EN/RU operations UI, Russian mock scenarios, and a CI application smoke check.

Next useful steps: a stronger similarity abstraction, an evaluation dataset with measurable triage quality, richer case navigation, and optional provider-specific cost configuration.

## Related project

This runnable demo complements my sanitized production architecture case study:

**[AI Support Agent — Case Study](https://github.com/damos17/ai-support-agent-case-study)**

---

Built as a public demonstration of **AI automation, agentic workflows, operational safety, observability, stateful systems and human-in-the-loop design**.
