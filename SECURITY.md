# Security

This repository is a **synthetic public demonstration**, not a production support platform.

## Demo boundaries

- No production customer data, credentials, internal endpoints, private prompts, or proprietary business rules are included.
- The default `LLM_MODE=mock` requires no external API key.
- Mutation endpoints such as ticket approval and demo reset intentionally have **no authentication** because the app is designed for local evaluation.
- Do not expose this demo to untrusted public traffic without adding authentication, authorization, session isolation, rate limiting, and deployment-specific hardening.
- SQLite is used to keep setup friction low. A production deployment should use database-managed identity/uniqueness, migrations, transactional consistency, backups, and an appropriate multi-process database.
- The bundled incident similarity engine is local and lexical. It is not presented as production-grade semantic incident detection.

## Browser safety

Dynamic API strings returned to the dashboard are HTML-escaped before rendering so user/model-provided markup is not interpreted as executable DOM content.

## Secrets

Use environment variables for provider credentials. `.env` files, local databases, virtual environments, and common local tooling files are excluded from both Git and Docker build context.

## Reporting

If you find a security issue in the public demo, please avoid posting sensitive exploit details in a public issue. Contact the repository owner through the GitHub profile instead.
