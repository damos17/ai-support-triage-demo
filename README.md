# AI Support Triage Agent

[![tests](https://github.com/damos17/ai-support-triage-demo/actions/workflows/tests.yml/badge.svg)](https://github.com/damos17/ai-support-triage-demo/actions/workflows/tests.yml)

A runnable, privacy-safe demonstration of an **AI support operations workflow**: issue detection, structured case creation, knowledge retrieval, escalation, cross-customer incident correlation, ticket drafting, persistence, auditability, telemetry, evaluation, and explicit human approval.

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
Pluggable similarity engine
      ↓
Cross-customer incident correlation
      ↓
Ticket draft
      ↓
EXPLICIT HUMAN APPROVAL
      ↓
Mock external ticket ID
```

Every meaningful transition is also written to a persistent audit trail. Provider latency and token usage are captured at the triage boundary when available.

The point is not to build another chat interface. The project demonstrates how an LLM can sit inside a controlled, stateful workflow where the surrounding system owns persistence, observability, permissions, evaluation and consequential actions.

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
- clickable recent-case navigation;
- case-detail view;
- persistent audit trail;
- LLM provider / latency / token / known-cost telemetry;
- explicit evaluation runner with visible quality metrics;
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

Audit events cover the main workflow transitions, including message receipt, triage, case creation, knowledge lookup, ticket drafting, incident detection, and explicit approval.

The database is ignored by Git so public repository history never accumulates local demo state.

## Incident correlation

The project exposes a `SimilarityEngine` boundary.

The default implementation is `TokenCosineSimilarity`: a local cosine-similarity engine over normalized token-frequency vectors. The incident detector combines:

- issue category;
- independent synthetic customer IDs;
- configurable similarity threshold;
- configurable minimum-customer threshold.

The default engine is deliberately local, dependency-light and explainable. It is **not** presented as production-grade semantic embeddings. The abstraction exists so a stronger embeddings-based implementation can replace it without changing incident orchestration.

## Evaluation

The repository contains a **16-row synthetic bilingual evaluation set** in `data/evaluation.json`: eight English and eight Russian cases covering noise, authentication, data ingestion, configuration, API, integration, performance, and billing.

The report exposes:

- exact row-level pass rate;
- issue / non-issue accuracy;
- category accuracy;
- severity accuracy;
- per-language metrics;
- per-category metrics;
- category confusion entries when misclassifications occur;
- row-level expected vs actual output.

Run the regression suite:

```bash
python -m pytest -q
```

Or inspect the current provider through:

```text
GET /api/evaluation
```

The UI also exposes an explicit **Run evaluation** action. It is not executed automatically because a real provider can incur API calls and cost.

The bundled dataset is intentionally small. It is a reproducible regression boundary, not a claim of real-world model quality.

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
GET  /api/cases?status=&category=&limit=
GET  /api/cases/{case_id}
GET  /api/incidents
GET  /api/audit
GET  /api/telemetry
GET  /api/evaluation
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
├── incidents.py     incident correlation orchestration
├── similarity.py    pluggable similarity boundary
├── evaluation.py    synthetic evaluation runner + metrics
├── ticketing.py     draft + approval gate
├── models.py        domain + audit models
└── templates/       bilingual operations dashboard

data/
├── scenarios.json   synthetic demo scenarios
└── evaluation.json  bilingual evaluation dataset

tests/
├── test_workflow.py
├── test_similarity.py
└── test_evaluation.py
```

## Tests

```bash
python -m pytest -q
```

The suite verifies workflow safety, persistence, auditability, telemetry, similarity behavior, and the full public bilingual evaluation dataset. GitHub Actions also performs a FastAPI version/import smoke check on every push and pull request.

## Engineering decisions

**Mock-first, real-model optional.** The project can be evaluated without an API key, but the LLM boundary is explicit and replaceable.

**State belongs to the application.** The model does not own case history, incident state, ticket state or authorization.

**Observability is part of the workflow.** Audit events and provider telemetry are application data, not console-only diagnostics.

**Evaluation is explicit.** A small versioned dataset makes quality checks repeatable instead of relying only on hand-picked UI examples.

**Similarity is replaceable.** Incident orchestration depends on a similarity interface rather than a hard-coded lexical algorithm.

**Evaluation does not run silently.** In the UI it is user-triggered, so switching to a paid provider does not create surprise model calls.

**Synthetic by construction.** No internal customer names, endpoints, credentials, prompts, production schemas, support conversations or proprietary business rules are included.

## Current version

**v0.5** expands the bilingual evaluation set to 16 cases, adds per-language/per-category metrics and category confusion reporting, introduces filtered recent-case navigation, and surfaces evaluation directly in the operations dashboard.

Next useful steps: optional embeddings-based similarity, provider-specific cost configuration, a larger adversarial evaluation set, and richer incident detail views.

## Related project

This runnable demo complements my sanitized production architecture case study:

**[AI Support Agent — Case Study](https://github.com/damos17/ai-support-agent-case-study)**

---

Built as a public demonstration of **AI automation, agentic workflows, operational safety, observability, evaluation, stateful systems and human-in-the-loop design**.
