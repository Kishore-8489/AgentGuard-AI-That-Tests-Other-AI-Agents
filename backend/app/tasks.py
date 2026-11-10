import logging
from uuid import UUID
try:
    from celery import Celery
except ImportError:  # Allows isolated offline tests without a Redis/Celery install.
    class Celery:  # type: ignore[no-redef]
        def __init__(self, *args, **kwargs):
            self.conf = self
        def update(self, **kwargs):
            pass
        def task(self, name: str):
            def wrap(fn):
                class LocalTask:
                    @staticmethod
                    def delay(*args, **kwargs):
                        if not settings.agentguard_eager:
                            raise RuntimeError("Install Celery for queued execution")
                        return fn(*args, **kwargs)
                return LocalTask()
            return wrap
from sqlalchemy import select
from app.config import settings
from app.db import SessionLocal
from app.models import AgentVersion, TestSuite, TestCase, TestRun, TestResult, ExecutionEvent, Finding, now
from app.agent import simulate_agent
from app.evaluator import evaluate

logger = logging.getLogger(__name__)
celery_app = Celery("agentguard", broker=settings.redis_url, backend=settings.redis_url)
celery_app.conf.update(
    task_always_eager=settings.agentguard_eager,
    task_store_eager_result=False,
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    worker_prefetch_multiplier=1,
    task_acks_late=True,
)


@celery_app.task(name="agentguard.execute_run")
def execute_run(run_id: str) -> None:
    """Idempotent logical results; this MVP is not a hardened distributed scheduler."""
    with SessionLocal() as session:
        run = session.get(TestRun, UUID(run_id))
        if run is None or run.status in {"completed", "cancelled"}:
            return
        try:
            run.status = "running"
            session.commit()
            version = session.get(AgentVersion, run.agent_version_id)
            suite = session.get(TestSuite, run.suite_id)
            if version is None or suite is None:
                raise ValueError("Missing referenced agent or suite")
            cases = session.scalars(select(TestCase).where(TestCase.suite_id == suite.id).order_by(TestCase.name)).all()
            if not cases:
                raise ValueError("Test suite contains no cases")
            for case in cases:
                existing = session.scalar(select(TestResult).where(
                    TestResult.run_id == run.id, TestResult.test_case_id == case.id))
                if existing is not None:
                    continue
                outcome = simulate_agent(version.profile, case.category, case.input_data)
                verdict = evaluate(outcome, case.expected)
                result = TestResult(run_id=run.id, test_case_id=case.id,
                                    status="passed" if verdict.passed else "failed",
                                    score=100 if verdict.passed else 0, output=outcome.output)
                session.add(result)
                session.flush()
                for index, (kind, detail) in enumerate(outcome.events):
                    session.add(ExecutionEvent(result_id=result.id, sequence=index,
                                               event_type=kind, detail=detail))
                for reason in verdict.reasons:
                    session.add(Finding(result_id=result.id, category=case.category,
                                        severity=case.severity, description=reason))
                session.commit()
            all_results = session.scalars(select(TestResult).where(TestResult.run_id == run.id)).all()
            run.score = round(sum(r.score for r in all_results) / len(all_results), 2)
            run.status = "completed"
            run.completed_at = now()
            session.commit()
        except Exception as exc:
            session.rollback()
            run = session.get(TestRun, UUID(run_id))
            if run is not None:
                run.status = "failed"
                run.error = str(exc)[:800]
                run.completed_at = now()
                session.commit()
            logger.exception("Run failed: %s", run_id)
            raise
