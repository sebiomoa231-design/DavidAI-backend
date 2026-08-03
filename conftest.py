import sys
from pathlib import Path

# Ensure the project root is importable when running pytest from anywhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient


@pytest.fixture(scope="session")
def client():
    from main import app
    return TestClient(app)
