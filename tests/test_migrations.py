import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest
from sqlalchemy import inspect, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session
from fastapi import HTTPException

from conftest import alembic
from app.models import Loan, User, Device
from app.schemas.loan_schema import LoanCreate
from app.services.loan_service import create_loan, return_loan


def test_upgrade_downgrade_and_metadata(tmp_path):
    path = tmp_path / "migration.db"
    for args in [("upgrade", "head"), ("check",), ("upgrade", "head"), ("history",), ("downgrade", "base"), ("upgrade", "head"), ("check",)]:
        result = alembic(path, *args)
        assert result.returncode == 0, result.stderr
    with sqlite3.connect(path) as db:
        assert {r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'")} == {"users", "devices", "loans", "alembic_version"}


def test_upgrade_preserves_existing_users(tmp_path):
    path = tmp_path / "legacy.db"
    assert alembic(path, "upgrade", "0001_users").returncode == 0
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO users VALUES (1, 'Ana Perez', 'ana@example.com', 'user', 1, 'original')")
    assert alembic(path, "upgrade", "head").returncode == 0
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT internal_notes FROM users").fetchone() == ("original",)
    assert alembic(path, "downgrade", "0001_users").returncode == 0
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT count(*) FROM users").fetchone() == (1,)


def test_adopt_unversioned_legacy_database(tmp_path):
    path = tmp_path / "unversioned.db"
    assert alembic(path, "upgrade", "0001_users").returncode == 0
    with sqlite3.connect(path) as db:
        db.execute("DROP TABLE alembic_version")
        db.execute("INSERT INTO users VALUES (1, 'Ana Perez', 'ana@example.com', 'user', 1, 'legacy')")
    assert alembic(path, "stamp", "0001_users").returncode == 0
    assert alembic(path, "upgrade", "head").returncode == 0
    assert alembic(path, "check").returncode == 0
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT internal_notes FROM users").fetchone() == ("legacy",)


def test_invalid_revision_and_url(tmp_path):
    assert alembic(tmp_path / "invalid.db", "upgrade", "does_not_exist").returncode != 0
    assert alembic(tmp_path / "missing" / "invalid.db", "upgrade", "head").returncode != 0


def test_foreign_keys_and_unique_open_loan(database, client, records):
    with database.begin() as connection:
        assert connection.scalar(text("PRAGMA foreign_keys")) == 1
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO loans (user_id, device_id) VALUES (999, 1)"))
        connection.execute(text("INSERT INTO loans (user_id, device_id) VALUES (1, 1)"))
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO loans (user_id, device_id) VALUES (1, 1)"))
        with pytest.raises(IntegrityError):
            connection.execute(text("DELETE FROM users WHERE id=1"))


def test_failed_commit_rolls_back_availability(database, client, records, monkeypatch):
    with Session(database) as db:
        def fail():
            raise SQLAlchemyError("simulated storage failure")
        monkeypatch.setattr(db, "commit", fail)
        with pytest.raises(HTTPException) as error:
            create_loan(db, LoanCreate(user_id=1, device_id=1))
        assert error.value.status_code == 500
    with Session(database) as db:
        assert db.get(Device, 1).is_available is True
        assert db.query(Loan).count() == 0


def test_concurrent_loans_only_one_succeeds(database, client, records):
    def attempt(_):
        with Session(database) as db:
            try:
                create_loan(db, LoanCreate(user_id=1, device_id=1))
                return 201
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(attempt, range(2))) == [201, 409]
    with Session(database) as db:
        assert db.query(Loan).count() == 1
        assert db.get(Device, 1).is_available is False


def test_failed_return_preserves_loan_and_availability(database, client, records, monkeypatch):
    with Session(database) as db:
        loan_id = create_loan(db, LoanCreate(user_id=1, device_id=1)).id
        def fail():
            raise SQLAlchemyError("simulated return failure")
        monkeypatch.setattr(db, "commit", fail)
        with pytest.raises(HTTPException) as error:
            return_loan(db, loan_id)
        assert error.value.status_code == 500
    with Session(database) as db:
        assert db.get(Loan, loan_id).status == "active"
        assert db.get(Loan, loan_id).return_date is None
        assert db.get(Device, 1).is_available is False


def test_concurrent_returns_only_one_succeeds(database, client, records):
    with Session(database) as db:
        loan_id = create_loan(db, LoanCreate(user_id=1, device_id=1)).id
    def attempt(_):
        with Session(database) as db:
            try:
                return_loan(db, loan_id)
                return 200
            except HTTPException as exc:
                return exc.status_code
    with ThreadPoolExecutor(max_workers=2) as executor:
        assert sorted(executor.map(attempt, range(2))) == [200, 409]


@pytest.mark.parametrize("values", ["1, 1, 'invalid', NULL", "1, 1, 'returned', NULL", "1, 1, 'active', '2026-01-01'", "1, 1, 'returned', '1900-01-01'", "1, 999, 'active', NULL"])
def test_loan_constraints(database, client, records, values):
    with database.begin() as connection:
        with pytest.raises(IntegrityError):
            connection.execute(text("INSERT INTO loans (user_id, device_id, status, return_date) VALUES (" + values + ")"))


def test_password_migration_preserves_existing_users_and_loans(tmp_path):
    path = tmp_path / "security-upgrade.db"
    assert alembic(path, "upgrade", "0d0e8b654860").returncode == 0
    with sqlite3.connect(path) as db:
        db.execute("INSERT INTO users VALUES (1, 'Ana Perez', 'ana@example.com', 'user', 1, 'legacy')")
        db.execute("INSERT INTO devices (id, name, serial_number, device_type) VALUES (1, 'Laptop', 'OLD-1', 'laptop')")
        db.execute("INSERT INTO loans (user_id, device_id) VALUES (1, 1)")
    assert alembic(path, "upgrade", "head").returncode == 0
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT hashed_password FROM users").fetchone() == (None,)
        assert db.execute("SELECT user_id, device_id FROM loans").fetchone() == (1, 1)
    assert alembic(path, "check").returncode == 0
    assert alembic(path, "downgrade", "0d0e8b654860").returncode == 0
    with sqlite3.connect(path) as db:
        assert db.execute("SELECT user_id, device_id FROM loans").fetchone() == (1, 1)
