"""AgentGuard v0.1: single-workspace demonstration API, not production SaaS auth."""
import asyncio
import json
import logging
from contextlib import asynccontextmanager
from uuid import UUID
from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from sqlalchemy import func, select
from sqlalchemy.orm import Session
from app.config import settings
from app.db import SessionLocal, get_db, init_db
from app.models import (Agent, AgentVersion, ExecutionEvent, Finding, Project,
                        TestCase, TestResult, TestRun, TestSuite)
from app.schemas import AgentIn, CompareIn, GateIn, GenerateIn, ProjectIn, RunIn, SuiteIn, VersionIn
from app.security import require_access
from app.generator import TEMPLATES, generate_cases
from app.tasks import execute_run

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    if not settings.demo_mode and not settings.agentguard_api_key:
        raise RuntimeError("Set AGENTGUARD_API_KEY when DEMO_MODE=false")
    init_db()
    yield


app = FastAPI(title="AgentGuard API", version="0.1.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=[x.strip() for x in settings.cors_origins.split(",")],
                   allow_credentials=False, allow_methods=["GET", "POST"],
                   allow_headers=["Content-Type", "X-API-Key", "Idempotency-Key"])

if settings.otel_enabled:
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    FastAPIInstrumentor.instrument_app(app)

api = "/api/v1"


def out_project(x: Project) -> dict:
    return {"id": str(x.id), "name": x.name}


def out_agent(x: Agent) -> dict:
    return {"id": str(x.id), "project_id": str(x.project_id), "name": x.name,
            "adapter_type": x.adapter_type}


def out_version(x: AgentVersion) -> dict:
    return {"id": str(x.id), "agent_id": str(x.agent_id), "version": x.version,
            "profile": x.profile}


def out_suite(x: TestSuite) -> dict:
    return {"id": str(x.id), "project_id": str(x.project_id), "name": x.name}


def out_case(x: TestCase) -> dict:
    return {"id": str(x.id), "suite_id": str(x.suite_id), "name": x.name,
            "category": x.category, "severity": x.severity,
            "input_data": x.input_data, "expected": x.expected}


def out_run(x: TestRun) -> dict:
    return {"id": str(x.id), "suite_id": str(x.suite_id),
            "agent_version_id": str(x.agent_version_id), "status": x.status,
            "score": x.score, "error": x.error,
            "created_at": x.created_at.isoformat() if x.created_at else None}


def out_result(x: TestResult, db: Session) -> dict:
    case = db.get(TestCase, x.test_case_id)
    return {"id": str(x.id), "run_id": str(x.run_id),
            "test_case_id": str(x.test_case_id), "category": case.category if case else "unknown",
            "name": case.name if case else "Unknown", "status": x.status,
            "score": x.score, "output": x.output}


def need(db: Session, model, identifier: UUID):
    found = db.get(model, identifier)
    if found is None:
        raise HTTPException(status_code=404, detail=f"{model.__name__} not found")
    return found


@app.get("/health")
def health():
    return {"status": "ok", "mode": "demo" if settings.demo_mode else "api-key"}


@app.get(f"{api}/projects", dependencies=[Depends(require_access)])
def projects(db: Session = Depends(get_db)):
    return [out_project(x) for x in db.scalars(select(Project).order_by(Project.name)).all()]


@app.post(f"{api}/projects", status_code=201, dependencies=[Depends(require_access)])
def create_project(payload: ProjectIn, db: Session = Depends(get_db)):
    if db.scalar(select(Project).where(Project.name == payload.name)):
        raise HTTPException(409, "Project name already exists")
    x = Project(name=payload.name)
    db.add(x)
    db.commit()
    db.refresh(x)
    return out_project(x)


@app.get(f"{api}/agents", dependencies=[Depends(require_access)])
def agents(db: Session = Depends(get_db)):
    return [out_agent(x) for x in db.scalars(select(Agent).order_by(Agent.name)).all()]


@app.post(f"{api}/agents", status_code=201, dependencies=[Depends(require_access)])
def create_agent(payload: AgentIn, db: Session = Depends(get_db)):
    need(db, Project, payload.project_id)
    x = Agent(**payload.model_dump())
    db.add(x)
    db.commit()
    db.refresh(x)
    return out_agent(x)


@app.get(f"{api}/agents/{{agent_id}}/versions", dependencies=[Depends(require_access)])
def versions(agent_id: UUID, db: Session = Depends(get_db)):
    need(db, Agent, agent_id)
    return [out_version(x) for x in db.scalars(select(AgentVersion).where(
        AgentVersion.agent_id == agent_id).order_by(AgentVersion.version)).all()]


@app.post(f"{api}/agents/{{agent_id}}/versions", status_code=201,
          dependencies=[Depends(require_access)])
def create_version(agent_id: UUID, payload: VersionIn, db: Session = Depends(get_db)):
    need(db, Agent, agent_id)
    if db.scalar(select(AgentVersion).where(AgentVersion.agent_id == agent_id,
                                            AgentVersion.version == payload.version)):
        raise HTTPException(409, "Version already exists")
    x = AgentVersion(agent_id=agent_id, **payload.model_dump())
    db.add(x)
    db.commit()
    db.refresh(x)
    return out_version(x)


@app.get(f"{api}/test-suites", dependencies=[Depends(require_access)])
def suites(db: Session = Depends(get_db)):
    return [out_suite(x) for x in db.scalars(select(TestSuite).order_by(TestSuite.name)).all()]


@app.post(f"{api}/test-suites", status_code=201, dependencies=[Depends(require_access)])
def create_suite(payload: SuiteIn, db: Session = Depends(get_db)):
    need(db, Project, payload.project_id)
    x = TestSuite(**payload.model_dump())
    db.add(x)
    db.commit()
    db.refresh(x)
    return out_suite(x)


@app.get(f"{api}/test-suites/{{suite_id}}/cases", dependencies=[Depends(require_access)])
def cases(suite_id: UUID, db: Session = Depends(get_db)):
    need(db, TestSuite, suite_id)
    return [out_case(x) for x in db.scalars(select(TestCase).where(TestCase.suite_id == suite_id)).all()]


@app.post(f"{api}/test-cases/generate", dependencies=[Depends(require_access)])
def generate(payload: GenerateIn, db: Session = Depends(get_db)):
    need(db, TestSuite, payload.suite_id)
    generated = generate_cases(payload.categories)
    created = []
    for item in generated:
        # Idempotent by suite/category for template-based MVP generation.
        row = db.scalar(select(TestCase).where(TestCase.suite_id == payload.suite_id,
                                               TestCase.category == item["category"]))
        if row is None:
            row = TestCase(suite_id=payload.suite_id, **item)
            db.add(row)
            db.flush()
        created.append(out_case(row))
    db.commit()
    return {"count": len(created), "cases": created}


@app.get(f"{api}/test-runs", dependencies=[Depends(require_access)])
def runs(db: Session = Depends(get_db)):
    return [out_run(x) for x in db.scalars(select(TestRun).order_by(
        TestRun.created_at.desc()).limit(50)).all()]


@app.post(f"{api}/test-runs", status_code=status.HTTP_202_ACCEPTED,
          dependencies=[Depends(require_access)])
def create_run(payload: RunIn, db: Session = Depends(get_db)):
    suite = need(db, TestSuite, payload.suite_id)
    version = need(db, AgentVersion, payload.agent_version_id)
    agent = need(db, Agent, version.agent_id)
    if suite.project_id != agent.project_id:
        raise HTTPException(422, "Suite and agent must belong to the same project")
    if not db.scalar(select(TestCase).where(TestCase.suite_id == suite.id).limit(1)):
        raise HTTPException(422, "Suite is empty; generate test cases first")
    row = TestRun(**payload.model_dump(), status="queued")
    db.add(row)
    db.commit()
    db.refresh(row)
    try:
        execute_run.delay(str(row.id))
    except Exception as exc:
        row.status = "failed"
        row.error = "Queue unavailable; retry creating run after restoring Redis"
        db.commit()
        logger.exception("Failed to enqueue run: %s", exc)
        raise HTTPException(503, "Queue unavailable; run marked failed") from exc
    db.refresh(row)
    return out_run(row)


@app.get(f"{api}/test-runs/{{run_id}}", dependencies=[Depends(require_access)])
def get_run(run_id: UUID, db: Session = Depends(get_db)):
    return out_run(need(db, TestRun, run_id))


@app.get(f"{api}/test-runs/{{run_id}}/results", dependencies=[Depends(require_access)])
def get_results(run_id: UUID, db: Session = Depends(get_db)):
    need(db, TestRun, run_id)
    rows = db.scalars(select(TestResult).where(TestResult.run_id == run_id)).all()
    return [out_result(x, db) for x in rows]


@app.get(f"{api}/test-results/{{result_id}}/trace", dependencies=[Depends(require_access)])
def trace(result_id: UUID, db: Session = Depends(get_db)):
    need(db, TestResult, result_id)
    rows = db.scalars(select(ExecutionEvent).where(
        ExecutionEvent.result_id == result_id).order_by(ExecutionEvent.sequence)).all()
    return [{"sequence": x.sequence, "event_type": x.event_type,
             "detail": x.detail, "timestamp": x.timestamp.isoformat()} for x in rows]


@app.get(f"{api}/test-runs/{{run_id}}/findings", dependencies=[Depends(require_access)])
def findings(run_id: UUID, db: Session = Depends(get_db)):
    need(db, TestRun, run_id)
    rows = db.execute(select(Finding, TestResult).join(TestResult, Finding.result_id == TestResult.id)
                      .where(TestResult.run_id == run_id)).all()
    return [{"id": str(f.id), "result_id": str(r.id), "category": f.category,
             "severity": f.severity, "description": f.description} for f, r in rows]


@app.post(f"{api}/test-results/{{result_id}}/replay", status_code=202,
          dependencies=[Depends(require_access)])
def replay(result_id: UUID, db: Session = Depends(get_db)):
    result = need(db, TestResult, result_id)
    run = need(db, TestRun, result.run_id)
    # Replay here means a fresh whole-suite regression run, not deterministic checkpoint replay.
    return create_run(RunIn(suite_id=run.suite_id, agent_version_id=run.agent_version_id), db)


@app.post(f"{api}/comparisons", dependencies=[Depends(require_access)])
def compare(payload: CompareIn, db: Session = Depends(get_db)):
    before = need(db, TestRun, payload.baseline_run_id)
    after = need(db, TestRun, payload.candidate_run_id)
    if before.status != "completed" or after.status != "completed":
        raise HTTPException(409, "Both test runs must be completed")
    if before.suite_id != after.suite_id:
        raise HTTPException(422, "Runs must use the same test suite")
    a = {x.test_case_id: x for x in db.scalars(select(TestResult).where(
        TestResult.run_id == before.id)).all()}
    b = {x.test_case_id: x for x in db.scalars(select(TestResult).where(
        TestResult.run_id == after.id)).all()}
    shared = a.keys() & b.keys()
    fixed = [str(key) for key in shared if a[key].status == "failed" and b[key].status == "passed"]
    regressions = [str(key) for key in shared if a[key].status == "passed" and b[key].status == "failed"]
    return {"baseline_score": before.score, "candidate_score": after.score,
            "score_delta": round((after.score or 0) - (before.score or 0), 2),
            "fixed_test_case_ids": fixed, "regressed_test_case_ids": regressions,
            "compared_cases": len(shared)}


@app.post(f"{api}/release-gates/evaluate", dependencies=[Depends(require_access)])
def release_gate(payload: GateIn, db: Session = Depends(get_db)):
    run = need(db, TestRun, payload.run_id)
    if run.status != "completed":
        raise HTTPException(409, "Cannot evaluate an unfinished run")
    critical = db.scalar(select(func.count()).select_from(Finding).join(
        TestResult, Finding.result_id == TestResult.id).where(
        TestResult.run_id == run.id, Finding.severity == "critical")) or 0
    passed = (run.score is not None and run.score >= payload.minimum_score
              and critical <= payload.maximum_critical_findings)
    return {"passed": passed, "run_id": str(run.id), "score": run.score,
            "critical_findings": critical, "minimum_score": payload.minimum_score}


@app.get(f"{api}/dashboard", dependencies=[Depends(require_access)])
def dashboard(db: Session = Depends(get_db)):
    total = db.scalar(select(func.count()).select_from(TestRun)) or 0
    completed = db.scalar(select(func.count()).select_from(TestRun).where(
        TestRun.status == "completed")) or 0
    last = db.scalar(select(TestRun).where(TestRun.status == "completed").order_by(
        TestRun.completed_at.desc()).limit(1))
    return {"total_runs": total, "completed_runs": completed,
            "latest_score": last.score if last else None}


@app.get(f"{api}/test-runs/{{run_id}}/events", dependencies=[Depends(require_access)])
async def run_events(run_id: UUID, db: Session = Depends(get_db)):
    need(db, TestRun, run_id)

    async def stream():
        # Short-lived one-way progress stream; no open session held across await.
        for _ in range(120):
            with SessionLocal() as local:
                row = local.get(TestRun, run_id)
                if row is None:
                    break
                event = out_run(row)
            yield f"event: status\ndata: {json.dumps(event)}\n\n"
            if event["status"] in {"completed", "failed", "cancelled"}:
                break
            await asyncio.sleep(1)
    return StreamingResponse(stream(), media_type="text/event-stream",
                             headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})


@app.post(f"{api}/demo/bootstrap", dependencies=[Depends(require_access)])
def bootstrap(db: Session = Depends(get_db)):
    if not settings.demo_mode:
        raise HTTPException(403, "Bootstrap is disabled outside demo mode")
    project = db.scalar(select(Project).where(Project.name == "AgentGuard Demo"))
    if project is None:
        project = Project(name="AgentGuard Demo")
        db.add(project)
        db.flush()
    agent = db.scalar(select(Agent).where(Agent.project_id == project.id,
                                          Agent.name == "Support Agent"))
    if agent is None:
        agent = Agent(project_id=project.id, name="Support Agent", adapter_type="demo")
        db.add(agent)
        db.flush()
    versions = {}
    for label, profile in [("v1.0", "vulnerable"), ("v1.1", "hardened")]:
        row = db.scalar(select(AgentVersion).where(AgentVersion.agent_id == agent.id,
                                                   AgentVersion.version == label))
        if row is None:
            row = AgentVersion(agent_id=agent.id, version=label, profile=profile)
            db.add(row)
            db.flush()
        versions[profile] = str(row.id)
    suite = db.scalar(select(TestSuite).where(TestSuite.project_id == project.id,
                                               TestSuite.name == "Adversarial Regression Suite"))
    if suite is None:
        suite = TestSuite(project_id=project.id, name="Adversarial Regression Suite")
        db.add(suite)
        db.flush()
    for category, item in TEMPLATES.items():
        row = db.scalar(select(TestCase).where(TestCase.suite_id == suite.id,
                                               TestCase.category == category))
        if row is None:
            db.add(TestCase(suite_id=suite.id, category=category, **item))
    db.commit()
    return {"project_id": str(project.id), "agent_id": str(agent.id),
            "suite_id": str(suite.id), "versions": versions}
