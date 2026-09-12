# AI Support Triage Agent

[![tests](https://github.com/damos17/ai-support-triage-demo/actions/workflows/tests.yml/badge.svg)](https://github.com/damos17/ai-support-triage-demo/actions/workflows/tests.yml)

A runnable, privacy-safe demonstration of an **AI support operations workflow**: issue detection, structured case creation, knowledge retrieval, escalation, cross-customer incident correlation, ticket drafting, and explicit human approval.

> **Public demo:** all customers, messages, rules, identifiers, and integrations are synthetic. This repository contains no production code or internal company data.

## Why this project exists

A useful AI system should do more than generate text. It should understand an operational event, maintain state, retrieve context, apply deterministic controls, prepare actions, and know when a human must approve the next step.

This project demonstrates that pattern in a small system that anyone can run locally without an API key.

## Demo flow

```text
Synthetic customer message
          ↓
      Triage engine
    noise / real issue
          ↓
    Structured case
          ↓
    Knowledge lookup
          ↓
     Decision layer
      solve / escalate
          ↓
  Incident correlation ──────┐
          ↓                   │
     Ticket draft             │
          ↓                   │
   HUMAN APPROVAL             │
          ↓                   │
    Mock ticket created       │
                              │
3+ related synthetic customers
          └───────────────────┘
        Potential incident
```

## What you can try

Open the web UI and submit messages such as:

```text
Thanks, everything works now.
```

The system classifies it as noise and creates no case.

Then try:

```text
Since this morning our data imports are failing with timeout errors.
```

The workflow creates a structured case, retrieves a synthetic knowledge-base recommendation, evaluates escalation, and prepares a mock ticket draft. The ticket remains a **draft until you explicitly approve it**.

To demonstrate incident correlation, submit similar data/import failures from three different customer IDs. The third independent report creates a potential incident.

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

## Mock-first by design

The default mode is deterministic and costs **$0**:

```env
LLM_MODE=mock
```

No API key is required. This makes the repository reproducible for reviewers and keeps automated tests stable.

The architecture reserves a provider-agnostic interface for an optional OpenAI-compatible LLM adapter. Real-model mode will remain opt-in and configured only through environment variables.

## API

FastAPI exposes:

```text
GET  /health
POST /api/messages
GET  /api/cases
GET  /api/incidents
POST /api/tickets/{case_id}/approve
```

Interactive OpenAPI documentation is available at `/docs` while the app is running.

## Engineering decisions

**Deterministic controls around AI.** Severity and approval policy are not delegated blindly to a language model. High-impact actions have explicit application-level gates.

**Human-in-the-loop.** Ticket creation is intentionally split into `draft` and `created` states. Generating a plausible action is not permission to execute it.

**Synthetic by construction.** The demo reimplements general architectural patterns from scratch. It does not contain copied production prompts, endpoints, customer information, credentials, internal schemas, or proprietary business rules.

**Mock-first provider abstraction.** Reviewers can understand and run the system before configuring a paid model. Real LLM support is an optional capability, not a prerequisite for the demo.

**Incident detection is configurable demo logic.** The current demo correlates multiple independent customers by issue category. A later iteration will add local semantic similarity while keeping the example thresholds separate from any production configuration.

## Safety invariant

The most important test in the repository is simple:

```text
AI may prepare a ticket.
AI may not create the ticket without explicit approval.
```

The test suite also verifies that conversational noise does not create cases and that three independent related reports can trigger a potential incident.

## Run tests

```bash
pytest -q
```

GitHub Actions runs the test suite on pushes and pull requests.

## Current scope

**v0.1** intentionally keeps the system small: FastAPI web UI, deterministic mock LLM, in-memory demo state, synthetic knowledge retrieval, incident correlation, mock ticketing, approval gate, Docker, tests, and CI.

Next iterations will add SQLite persistence, a clean provider interface with optional OpenAI-compatible mode, local semantic similarity, richer scenario fixtures, an audit trail, and a more visual operations dashboard.

## Related project

This runnable demo complements my sanitized production architecture case study:

**[AI Support Agent — Case Study](https://github.com/damos17/ai-support-agent-case-study)**

---

Built as a public demonstration of **AI automation, agentic workflows, operational safety, and human-in-the-loop system design**.
