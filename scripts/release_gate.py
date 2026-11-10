"""CI release-gate helper. Exit 0 only when an AgentGuard run passes policy."""
import argparse
import json
import sys
import urllib.error
import urllib.request


def main() -> int:
    p = argparse.ArgumentParser(description="Evaluate AgentGuard CI release gate")
    p.add_argument("--base-url", default="http://127.0.0.1:8000")
    p.add_argument("--run-id", required=True)
    p.add_argument("--api-key", default="")
    p.add_argument("--minimum-score", type=float, default=90)
    p.add_argument("--maximum-critical", type=int, default=0)
    args = p.parse_args()
    payload = json.dumps({"run_id": args.run_id, "minimum_score": args.minimum_score,
                          "maximum_critical_findings": args.maximum_critical}).encode()
    headers = {"Content-Type": "application/json"}
    if args.api_key:
        headers["X-API-Key"] = args.api_key
    req = urllib.request.Request(args.base_url.rstrip("/") + "/api/v1/release-gates/evaluate",
                                 data=payload, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=30) as response:
            report = json.load(response)
    except (urllib.error.URLError, ValueError) as exc:
        print("AgentGuard gate could not be evaluated:", exc, file=sys.stderr)
        return 2
    print(json.dumps(report, indent=2))
    return 0 if report.get("passed") is True else 1


if __name__ == "__main__":
    sys.exit(main())
