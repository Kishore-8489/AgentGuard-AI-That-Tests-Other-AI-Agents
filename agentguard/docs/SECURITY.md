# Security design and current limitations

## Critical boundary

**This is a single-workspace demonstration, not a production sandbox.** No real customer integrations, arbitrary code execution, remote agent endpoints, or unrestricted tool execution are implemented. The demo `simulate_agent()` records a `tool.attempt` event with `executed: false`; it never exports customer data or issues refunds.

## Configurations

- `DEMO_MODE=true` bypasses authentication. Use only on a trusted local machine, with loopback-only bindings as in `docker-compose.yml`.
- `DEMO_MODE=false` requires a non-empty `AGENTGUARD_API_KEY` and an `X-API-Key` request header. This is a minimal developer authentication mechanism, **not** multi-tenant authorization.
- No user login is implemented in the frontend. Do not expose the dashboard publicly without an appropriate identity layer.
- DB/Redis credentials in Compose are local development defaults. Replace credentials and use secret management for any external deployment.
- The demo intentionally records synthetic prompt and retrieval content in PostgreSQL. Do not send real customer PII or secrets.

## Threat model and roadmap

| Threat | Current mitigation | Required for production |
|---|---|---|
| Untrusted code execution | Not supported | Isolated runner/microVM; non-root; read-only root; quotas |
| SSRF | External endpoints not implemented | Egress policy gateway, DNS/IP validation, redirect restrictions |
| Credential leakage | No real secrets in demo fixtures | Managed secrets, short-lived scopes, redaction |
| Tenant data access | Single workspace only | OIDC, per-project scopes, PostgreSQL RLS |
| Queue replay | Unique logical result keys | Transactional outbox, leases, fencing tokens |
| Test data integrity | Test suite IDs and versions stored | Immutable snapshots, signed artifact hashes |
| Data retention | Persistent local DB | Configurable deletion, encrypted artifacts, audit trail |
| Prompt injection | Deterministic failure checks | Evaluator isolation and trust-boundary enforcement |

## Reporting a vulnerability

Please do not publish exploit details in public issues. Contact the repository owner privately through the channel advertised in the GitHub repository security settings. Once the repository is created, configure GitHub private vulnerability reporting and publish SECURITY.md contact guidance.

## Deployment checklist

1. Turn off demo mode.
2. Add an identity provider and per-resource authorization.
3. Move persistence to managed PostgreSQL with migrations and backups.
4. Introduce encrypted artifact storage and controlled retention.
5. Implement immutable run configuration, reliable task ownership and reconciliation.
6. Add a fully isolated runner **before** integrating arbitrary agents.
7. Review SSRF, egress, secrets and log/redaction boundaries.
8. Conduct cross-tenant, adversarial, and load testing.
