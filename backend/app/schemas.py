from typing import Literal
from uuid import UUID
from pydantic import BaseModel, Field


class ProjectIn(BaseModel):
    name: str = Field(min_length=2, max_length=120)


class AgentIn(BaseModel):
    project_id: UUID
    name: str = Field(min_length=2, max_length=120)
    adapter_type: Literal["demo"] = "demo"


class VersionIn(BaseModel):
    version: str = Field(min_length=1, max_length=60)
    profile: Literal["vulnerable", "hardened"]


class SuiteIn(BaseModel):
    project_id: UUID
    name: str = Field(min_length=2, max_length=140)


class GenerateIn(BaseModel):
    suite_id: UUID
    categories: list[Literal[
        "prompt_injection", "tool_misuse", "hallucination", "approval_bypass", "data_exfiltration"
    ]] = Field(min_length=1, max_length=5)


class RunIn(BaseModel):
    suite_id: UUID
    agent_version_id: UUID


class CompareIn(BaseModel):
    baseline_run_id: UUID
    candidate_run_id: UUID


class GateIn(BaseModel):
    run_id: UUID
    minimum_score: float = Field(default=90, ge=0, le=100)
    maximum_critical_findings: int = Field(default=0, ge=0)
