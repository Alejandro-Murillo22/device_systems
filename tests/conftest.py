import os
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker

from app.database.database import get_db
from app.main import app

ROOT = Path(__file__).resolve().parents[1]


def alembic(database, *args):
    env = {**os.environ, "DATABASE_URL": f"sqlite:///{database.as_posix()}"}
    return subprocess.run([sys.executable, "-m", "alembic", *args], cwd=ROOT, env=env, capture_output=True, text=True)


@pytest.fixture
def database(tmp_path):
    path = tmp_path / "test.db"
    result = alembic(path, "upgrade", "head")
    assert result.returncode == 0, result.stderr
    engine = create_engine(f"sqlite:///{path.as_posix()}", connect_args={"check_same_thread": False})

    @event.listens_for(engine, "connect")
    def foreign_keys(connection, _):
        connection.execute("PRAGMA foreign_keys=ON")

    yield engine
    engine.dispose()


@pytest.fixture
def client(database, monkeypatch):
    monkeypatch.setenv("API_KEY", "test-key")
    factory = sessionmaker(database)

    def session():
        with factory() as db:
            yield db

    app.dependency_overrides[get_db] = session
    with TestClient(app, raise_server_exceptions=False) as client:
        yield client
    app.dependency_overrides.clear()


@pytest.fixture
def records(client):
    user = client.post("/users", json={"name": "Ana Perez", "email": "ana@example.com"})
    device = client.post("/devices", json={"name": "ThinkPad", "serial_number": "LEN-001", "device_type": "laptop", "brand": "lenovo"})
    assert user.status_code == device.status_code == 201
    return user.json(), device.json()
