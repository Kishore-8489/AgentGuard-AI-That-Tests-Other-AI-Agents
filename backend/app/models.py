import uuid
from datetime import datetime, timezone
from typing import Any
from sqlalchemy import DateTime, ForeignKey, Integer, JSON, String, Text, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column
from app.db import Base


def uid() -> uuid.UUID:
    return uuid.uuid4()


def now() -> datetime:
    return datetime.now(timezone.utc)


class Project(Base):
    __tablename__ = "projects"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uid)
    name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Agent(Base):
    __tablename__ = "agents"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uid)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(120), nullable=False)
    adapter_type: Mapped[str] = mapped_column(String(30), default="demo")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class AgentVersion(Base):
    __tablename__ = "agent_versions"
    __table_args__ = (UniqueConstraint("agent_id", "version"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uid)
    agent_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agents.id"), nullable=False, index=True)
    version: Mapped[str] = mapped_column(String(60), nullable=False)
    profile: Mapped[str] = mapped_column(String(20), nullable=False)  # vulnerable | hardened
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TestSuite(Base):
    __tablename__ = "test_suites"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uid)
    project_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("projects.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(140), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class TestCase(Base):
    __tablename__ = "test_cases"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uid)
    suite_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_suites.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(180), nullable=False)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    severity: Mapped[str] = mapped_column(String(12), nullable=False)
    input_data: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    expected: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)


class TestRun(Base):
    __tablename__ = "test_runs"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uid)
    suite_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_suites.id"), nullable=False, index=True)
    agent_version_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("agent_versions.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(30), default="queued", index=True)
    score: Mapped[float | None] = mapped_column(nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TestResult(Base):
    __tablename__ = "test_results"
    __table_args__ = (UniqueConstraint("run_id", "test_case_id"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uid)
    run_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_runs.id"), nullable=False, index=True)
    test_case_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_cases.id"), nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="pending")
    score: Mapped[float] = mapped_column(default=0)
    output: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class ExecutionEvent(Base):
    __tablename__ = "execution_events"
    __table_args__ = (UniqueConstraint("result_id", "sequence"),)
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uid)
    result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_results.id"), nullable=False, index=True)
    sequence: Mapped[int] = mapped_column(Integer, nullable=False)
    event_type: Mapped[str] = mapped_column(String(60), nullable=False)
    detail: Mapped[dict[str, Any]] = mapped_column(JSON, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=now)


class Finding(Base):
    __tablename__ = "findings"
    id: Mapped[uuid.UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uid)
    result_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("test_results.id"), nullable=False, index=True)
    category: Mapped[str] = mapped_column(String(60), nullable=False)
    severity: Mapped[str] = mapped_column(String(12), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
