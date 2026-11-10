# Contributing to AgentGuard

Thank you for helping build trustworthy agent testing tools.

## Development flow

1. Fork the repository and create a `feat/<topic>` or `fix/<topic>` branch.
2. Keep PRs focused: describe the threat model, expected behavior, and evidence.
3. Run backend pytest and frontend TypeScript build before submitting.
4. Include a regression test for every fixed failure detector.
5. Never include customer secrets, sensitive datasets, or executable attack payloads targeting real systems in tests.

## Code review principles

- Prefer deterministic evidence over uncalibrated LLM judgments.
- Do not run user-controlled code in the trusted API or worker process.
- Any new real agent adapter must include a separate isolation/security design review.
- Clearly distinguish simulator behavior from real security guarantees.

## Security reports

Report vulnerabilities privately; see `docs/SECURITY.md`.
