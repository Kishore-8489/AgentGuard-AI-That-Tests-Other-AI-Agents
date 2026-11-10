from uuid import uuid4
from app.agent import simulate_agent
from app.evaluator import evaluate
from app.generator import generate_cases


def test_health_and_bootstrap_idempotent(client):
    assert client.get("/health").json()["status"] == "ok"
    a = client.post("/api/v1/demo/bootstrap").json()
    b = client.post("/api/v1/demo/bootstrap").json()
    assert a == b
    assert len(client.get(f"/api/v1/test-suites/{a['suite_id']}/cases").json()) == 5


def test_end_to_end_regression_and_release_gate(client):
    demo = client.post("/api/v1/demo/bootstrap").json()
    run_ids = {}
    for profile, expected_score in (("vulnerable", 0), ("hardened", 100)):
        response = client.post("/api/v1/test-runs", json={
            "suite_id": demo["suite_id"],
            "agent_version_id": demo["versions"][profile],
        })
        assert response.status_code == 202, response.text
        run = response.json()
        assert run["status"] == "completed"
        assert run["score"] == expected_score
        run_ids[profile] = run["id"]
        results = client.get(f"/api/v1/test-runs/{run['id']}/results").json()
        assert len(results) == 5
        trace = client.get(f"/api/v1/test-results/{results[0]['id']}/trace").json()
        assert len(trace) >= 3
        assert trace[0]["event_type"] == "input"
        gate = client.post("/api/v1/release-gates/evaluate", json={"run_id": run["id"]})
        assert gate.status_code == 200
        assert gate.json()["passed"] == (profile == "hardened")
    comparison = client.post("/api/v1/comparisons", json={
        "baseline_run_id": run_ids["vulnerable"],
        "candidate_run_id": run_ids["hardened"],
    }).json()
    assert comparison["score_delta"] == 100
    assert len(comparison["fixed_test_case_ids"]) == 5
    assert comparison["regressed_test_case_ids"] == []
    findings = client.get(f"/api/v1/test-runs/{run_ids['vulnerable']}/findings").json()
    assert any(f["severity"] == "critical" for f in findings)


def test_cross_project_run_is_rejected(client):
    demo = client.post("/api/v1/demo/bootstrap").json()
    project = client.post("/api/v1/projects", json={"name": "Project " + str(uuid4())}).json()
    suite = client.post("/api/v1/test-suites", json={
        "project_id": project["id"], "name": "Isolated Suite"
    }).json()
    response = client.post("/api/v1/test-runs", json={
        "suite_id": suite["id"], "agent_version_id": demo["versions"]["vulnerable"]
    })
    assert response.status_code == 422


def test_deterministic_evidence_verdict():
    case = generate_cases(["prompt_injection"])[0]
    bad = simulate_agent("vulnerable", case["category"], case["input_data"])
    good = simulate_agent("hardened", case["category"], case["input_data"])
    assert not evaluate(bad, case["expected"]).passed
    assert evaluate(good, case["expected"]).passed
    assert any(e[0] == "tool.attempt" for e in bad.events)
    assert all(e[0] != "tool.attempt" for e in good.events)


def test_generation_idempotent(client):
    demo = client.post("/api/v1/demo/bootstrap").json()
    response = client.post("/api/v1/test-cases/generate", json={
        "suite_id": demo["suite_id"],
        "categories": ["prompt_injection", "hallucination"],
    })
    assert response.status_code == 200
    assert response.json()["count"] == 2
    assert len(client.get(f"/api/v1/test-suites/{demo['suite_id']}/cases").json()) == 5


def test_missing_resource_not_found(client):
    response = client.get(f"/api/v1/test-runs/{uuid4()}")
    assert response.status_code == 404
