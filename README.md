# AI Support Triage Agent

[![tests](https://github.com/damos17/ai-support-triage-demo/actions/workflows/tests.yml/badge.svg)](https://github.com/damos17/ai-support-triage-demo/actions/workflows/tests.yml)

A runnable, privacy-safe demonstration of an **AI support operations workflow**: issue detection, structured case creation, knowledge retrieval, escalation, cross-customer incident correlation, ticket drafting, persistence, and explicit human approval.

> **Public demo:** all customers, messages, rules, identifiers, and integrations are synthetic. This repository contains no production code or internal company data.

## What it demonstrates

The demo accepts synthetic support messages and moves them through an operational pipeline:

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

The point is not to build another chat interface. The project demonstrates how an LLM can sit inside a controlled, stateful workflow where the surrounding system owns persistence, permissions and consequential actions.

## Quick start

### Docker

```bash
git clone https://github.com/damos17/ai-support-triage-demo.git
cd ai-support-triage-demo
docker compose up --build
```

Open `http://localhost:8000`.

### Python

```bash
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

The interactive API documentation is available at `http://localhost:8000/docs`.

## Operations dashboard

The web UI includes:

- synthetic scenario presets;
- live workflow stages;
- case / severity / confidence output;
- knowledge-base guidance;
- potential incident alerts;
- ticket approval controls;
- counters for cases, incidents, drafts and approved tickets;
- one-click three-customer incident demo;
- resettable demo state.

## Mock mode: zero cost

The default configuration is deterministic and requires no external service:

```env
LLM_MODE=mock
```

This keeps the demo reproducible and makes CI deterministic.

## Optional real LLM mode

The workflow now uses a provider interface rather than depending directly on one model vendor. An OpenAI-compatible endpoint can be enabled through environment variables:

```env
LLM_MODE=openai_compatible
LLM_BASE_URL=https://your-provider.example/v1
LLM_API_KEY=...
LLM_MODEL=...
```

Only the triage boundary is exposed to the provider. Approval policy, persistence and ticket execution remain application responsibilities.

## Persistence

Demo state is stored in SQLite under `data/demo.db` by default. Cases, ticket drafts and incidents survive an application restart.

The database is intentionally ignored by Git so public repository history never accumulates local demo state.

## Incident correlation

v0.2 uses a transparent local correlator based on:

- issue category;
- independent synthetic customer IDs;
- token overlap between issue descriptions;
- a configurable minimum-customer threshold.

This is deliberately lightweight and explainable. It demonstrates the workflow boundary without pretending that simple token overlap is production-grade semantic similarity.

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
GET  /api/incidents
GET  /api/stats
GET  /api/scenarios
POST /api/tickets/{case_id}/approve
POST /api/reset
```

## Project structure

```text
app/
├── main.py          FastAPI routes and UI entry point
├── workflow.py      orchestration and state transitions
├── llm.py           provider interface + mock/OpenAI-compatible providers
├── db.py            SQLite persistence
├── knowledge.py     synthetic retrieval boundary
├── incidents.py     incident correlation
├── ticketing.py     draft + approval gate
├── models.py        domain models
└── templates/       operations dashboard

data/
└── scenarios.json   synthetic demo scenarios

tests/
└── test_workflow.py safety, incident and persistence tests
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
- approved tickets receive only mock IDs;
- workflow state survives a restart.

GitHub Actions runs the suite on every push and pull request.

## Engineering decisions

**Mock-first, real-model optional.** The project can be evaluated without an API key, but the LLM boundary is explicit and replaceable.

**State belongs to the application.** The model does not own case history, incident state, ticket state or authorization.

**Synthetic by construction.** No internal customer names, endpoints, credentials, prompts, production schemas, support conversations or proprietary business rules are included.

**Modular instead of monolithic.** Triage, persistence, retrieval, incident correlation and ticketing are separated so each boundary can evolve independently.

## Current version

**v0.2** adds SQLite persistence, provider abstraction, an optional OpenAI-compatible triage provider, modular services, richer synthetic scenarios, a visual operations dashboard and persistence tests.

Next useful steps: stronger local semantic similarity, audit events, cost/token telemetry, case-detail views and a small evaluation dataset.

## Related project

This runnable demo complements my sanitized production architecture case study:

**[AI Support Agent — Case Study](https://github.com/damos17/ai-support-agent-case-study)**

---

Built as a public demonstration of **AI automation, agentic workflows, operational safety, stateful systems and human-in-the-loop design**.
