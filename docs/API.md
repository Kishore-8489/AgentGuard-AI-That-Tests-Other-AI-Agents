# API reference

Use `/docs` for FastAPI's generated OpenAPI schema. All endpoints below are under `/api/v1`; `/health` is public.

| Method | Path | Description |
|---|---|---|
| GET | `/projects` | List projects |
| POST | `/projects` | Create project |
| GET | `/agents` | List agents |
| POST | `/agents` | Register demo agent |
| GET | `/agents/{id}/versions` | List agent versions |
| POST | `/agents/{id}/versions` | Register immutable demo version |
| GET | `/test-suites` | List test suites |
| POST | `/test-suites` | Create suite |
| GET | `/test-suites/{id}/cases` | List cases |
| POST | `/test-cases/generate` | Generate/deduplicate deterministic LangGraph cases |
| GET | `/test-runs` | List recent campaigns |
| POST | `/test-runs` | Queue a campaign |
| GET | `/test-runs/{id}` | Campaign status |
| GET | `/test-runs/{id}/results` | All case results |
| GET | `/test-runs/{id}/findings` | Trace-backed failures |
| GET | `/test-runs/{id}/events` | SSE progress stream |
| GET | `/test-results/{id}/trace` | Execution timeline |
| POST | `/test-results/{id}/replay` | Fresh whole-suite regression (not exact replay) |
| POST | `/comparisons` | Compare two complete runs of the same suite |
| POST | `/release-gates/evaluate` | Score/critical-count release decision |
| GET | `/dashboard` | Run summary |
| POST | `/demo/bootstrap` | Seed safe local fixtures (demo mode only) |

## Example test execution

First `POST /demo/bootstrap` with `{}`. Then:

```json
POST /test-runs
{
  "suite_id": "<uuid from bootstrap>",
  "agent_version_id": "<uuid from bootstrap.versions.vulnerable>"
}
```

This returns `202 Accepted`. Poll `GET /test-runs/{id}` until `status=completed` or `failed`. Compare with an analogous run against `bootstrap.versions.hardened`.

The service currently supports only `adapter_type=demo` and version profile `vulnerable` or `hardened`. This restriction intentionally prevents arbitrary code or remote network execution.
