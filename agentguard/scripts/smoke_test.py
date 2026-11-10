"""End-to-end API smoke test against running Docker Compose installation."""
import sys
import time
import urllib.request
import json

BASE = "http://127.0.0.1:8000/api/v1"


def request(path: str, body: dict | None = None):
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(BASE + path, data=data, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=15) as response:
        return json.load(response)


def wait_run(run_id):
    for _ in range(45):
        row = request(f"/test-runs/{run_id}")
        if row["status"] == "completed":
            return row
        if row["status"] == "failed":
            raise RuntimeError(f"run failed: {row['error']}")
        time.sleep(1)
    raise TimeoutError(f"run did not finish: {run_id}")


def main():
    demo = request("/demo/bootstrap", {})
    runs = []
    for profile in ("vulnerable", "hardened"):
        run = request("/test-runs", {"suite_id": demo["suite_id"],
                                     "agent_version_id": demo["versions"][profile]})
        completed = wait_run(run["id"])
        print(profile, completed["score"], completed["status"])
        runs.append(completed)
    compare = request("/comparisons", {"baseline_run_id": runs[0]["id"],
                                       "candidate_run_id": runs[1]["id"]})
    assert runs[0]["score"] < runs[1]["score"]
    assert compare["fixed_test_case_ids"]
    print("PASS: version improvement and regression comparison verified")


if __name__ == "__main__":
    try:
        main()
    except Exception as exc:
        print(f"FAIL: {exc}", file=sys.stderr)
        sys.exit(1)
