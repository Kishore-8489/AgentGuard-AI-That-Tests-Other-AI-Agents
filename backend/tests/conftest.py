"""Tests use an isolated SQLite database and synchronous Celery execution."""
import os
import tempfile
from pathlib import Path

TEST_DB = Path(tempfile.mkdtemp(prefix="agentguard_tests_")) / "test.db"
os.environ["DATABASE_URL"] = f"sqlite:///{TEST_DB}"
os.environ["DEMO_MODE"] = "true"
os.environ["AGENTGUARD_EAGER"] = "true"

import pytest  # noqa: E402
from fastapi.testclient import TestClient  # noqa: E402
from app.main import app  # noqa: E402


@pytest.fixture(scope="session")
def client():
    with TestClient(app) as api:
        yield api
