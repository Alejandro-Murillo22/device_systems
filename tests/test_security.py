from datetime import timedelta
import logging

import pytest
from fastapi.testclient import TestClient
from jose import jwt
from pydantic import ValidationError
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.config import Settings
from app.database.database import get_db
from app.main import create_app
from app.models import Device, User
from app.rate_limit import limiter
from app.security import ALGORITHM, AUDIENCE, ISSUER, create_access_token, hash_password, verify_password

PASSWORD = "ClaveDePrueba2026!"
SETTINGS = Settings(secret_key="test-signing-key-only-for-automated-tests-12345678")


@pytest.fixture
def security_app(database):
    application = create_app(SETTINGS)
    def session():
        with Session(database) as db:
            yield db
    application.dependency_overrides[get_db] = session
    limiter.reset()
    yield application
    limiter.reset()


@pytest.fixture
def anonymous(security_app):
    with TestClient(security_app, raise_server_exceptions=False) as client:
        yield client


def register(client, email="ana@example.com", password=PASSWORD):
    return client.post("/register", json={"name": "Ana Perez", "email": email, "password": password})


def login(client, email="ana@example.com", password=PASSWORD):
    return client.post("/token", data={"username": email, "password": password})


def headers(token):
    return {"Authorization": "Bearer " + token}


def test_bcrypt_unique_salts_and_unicode_limit():
    first, second = hash_password(PASSWORD), hash_password(PASSWORD)
    assert first != second and first.startswith("$2b$12$")
    assert verify_password(PASSWORD, first) and verify_password(PASSWORD, second)
    assert not verify_password("wrong", first)
    assert not verify_password(PASSWORD, "corrupt-hash")
    with pytest.raises(ValueError):
        hash_password("é" * 37)
    assert not verify_password("a" * 73, first)


def test_register_login_profile_and_private_fields(anonymous, database):
    response = register(anonymous)
    assert response.status_code == 201
    assert response.json()["role"] == "user"
    assert {"password", "hashed_password", "internal_notes"}.isdisjoint(response.json())
    with Session(database) as db:
        user = db.scalar(select(User))
        assert verify_password(PASSWORD, user.hashed_password)
        assert user.hashed_password != PASSWORD
    token = login(anonymous)
    assert token.status_code == 200
    assert token.headers["Cache-Control"] == "no-store"
    assert token.json()["token_type"] == "bearer"
    assert token.json()["expires_in"] == 1800
    profile = anonymous.get("/users/me", headers=headers(token.json()["access_token"]))
    assert profile.status_code == 200
    assert profile.json()["email"] == "ana@example.com"
    assert {"password", "hashed_password", "internal_notes"}.isdisjoint(profile.json())


@pytest.mark.parametrize("payload", [
    {"name": "   ", "email": "ana@example.com", "password": PASSWORD},
    {"name": "Ana", "email": "invalid", "password": PASSWORD},
    {"name": "Ana", "email": "ana@example.com", "password": "S3cr!"},
    {"name": "Ana", "email": "ana@example.com", "password": "é" * 37},
    {"name": "Ana", "email": "ana@example.com", "password": "a" * 73},
    {"name": "Ana", "email": "ana@example.com", "password": "null\x00byte"},
    {"name": "Ana", "email": "ana@example.com", "password": PASSWORD, "role": "admin"},
])
def test_registration_validation_never_echoes_password(anonymous, payload):
    result = anonymous.post("/register", json=payload)
    assert result.status_code == 422
    assert payload["password"] not in result.text
    assert all("input" not in error for error in result.json()["detail"])


def test_duplicates_and_bad_credentials(anonymous):
    assert register(anonymous).status_code == 201
    assert register(anonymous, "ANA@example.com").status_code == 400
    missing = login(anonymous, "missing@example.com")
    wrong = login(anonymous, password="incorrect")
    assert missing.status_code == wrong.status_code == 401
    assert missing.json() == wrong.json()
    assert wrong.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("path", ["/users", "/users/me", "/devices", "/loans", "/loans/details"])
def test_missing_tokens_rejected(anonymous, path):
    response = anonymous.get(path)
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


@pytest.mark.parametrize("kind", ["malformed", "expired", "signature", "missing_exp", "missing_sub", "bad_sub", "algorithm", "deleted"])
def test_invalid_tokens_rejected(anonymous, kind):
    register(anonymous)
    if kind == "malformed":
        token = "not-a-token"
    elif kind == "expired":
        token = create_access_token(1, SETTINGS, timedelta(seconds=-60))
    elif kind == "deleted":
        token = create_access_token(999, SETTINGS)
    else:
        data = {"sub": "1", "exp": 4102444800, "iat": 1, "aud": AUDIENCE, "iss": ISSUER}
        key = SETTINGS.secret_key.get_secret_value()
        if kind == "signature":
            key = "another-signing-key-of-at-least-32-characters"
        elif kind == "missing_exp":
            del data["exp"]
        elif kind == "missing_sub":
            del data["sub"]
        elif kind == "bad_sub":
            data["sub"] = "abc"
        token = jwt.encode(data, key, algorithm="HS384" if kind == "algorithm" else ALGORITHM)
    result = anonymous.get("/users/me", headers=headers(token))
    assert result.status_code == 401


def test_inactive_user_and_role_changes_checked_in_database(anonymous, database):
    register(anonymous)
    token = login(anonymous).json()["access_token"]
    with Session(database) as db:
        user = db.get(User, 1)
        user.is_active = False
        db.commit()
    assert anonymous.get("/users/me", headers=headers(token)).status_code == 403
    assert login(anonymous).status_code == 403


def test_legacy_user_cannot_login_without_password(anonymous, database):
    with Session(database) as db:
        db.add(User(name="Legacy User", email="legacy@example.com", role="user", is_active=True))
        db.commit()
    assert login(anonymous, "legacy@example.com").status_code == 401
    assert anonymous.get("/users/me", headers=headers(create_access_token(1, SETTINGS))).status_code == 401


def test_permissions_and_loan_ownership(anonymous, database):
    register(anonymous)
    register(anonymous, "other@example.com")
    owner_headers = headers(login(anonymous).json()["access_token"])
    other_headers = headers(login(anonymous, "other@example.com").json()["access_token"])
    with Session(database) as db:
        db.add(Device(name="Laptop", serial_number="AUTH-1", device_type="laptop"))
        db.commit()
    assert anonymous.get("/devices", headers=owner_headers).status_code == 200
    assert anonymous.post("/devices", headers=owner_headers, json={"name": "Tablet", "serial_number": "AUTH-2", "device_type": "tablet"}).status_code == 403
    assert anonymous.get("/users", headers=owner_headers).status_code == 403
    assert anonymous.patch("/users/1", headers=owner_headers, json={"role": "admin"}).status_code == 403
    assert anonymous.get("/users/2", headers=owner_headers).status_code == 403
    assert anonymous.post("/loans", headers=owner_headers, json={"user_id": 2, "device_id": 1}).status_code == 403
    loan = anonymous.post("/loans", headers=owner_headers, json={"user_id": 1, "device_id": 1})
    assert loan.status_code == 201
    assert anonymous.get("/loans", headers=other_headers).json() == []
    assert anonymous.get("/loans?user_id=1", headers=other_headers).status_code == 403
    assert anonymous.get("/loans/1", headers=other_headers).status_code == 403
    assert anonymous.patch("/loans/1/return", headers=other_headers).status_code == 403
    assert anonymous.get("/devices/1/loans", headers=other_headers).status_code == 403
    assert anonymous.patch("/loans/1/return", headers=owner_headers).status_code == 200


def test_login_rate_limit_and_cors_headers(anonymous):
    for _ in range(5):
        assert login(anonymous).status_code == 401
    response = anonymous.post("/token", data={"username": "unknown@example.com", "password": PASSWORD}, headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 429
    assert int(response.headers["Retry-After"]) >= 0
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert "X-Correlation-ID" in response.headers


def test_profile_limit_uses_verified_user_not_token_or_ip(anonymous):
    register(anonymous)
    register(anonymous, "second@example.com")
    first_token = login(anonymous).json()["access_token"]
    second_token = login(anonymous).json()["access_token"]
    another_user_token = login(anonymous, "second@example.com").json()["access_token"]
    for _ in range(30):
        assert anonymous.get("/users/me", headers=headers(first_token)).status_code == 200
    assert anonymous.get("/users/me", headers=headers(second_token)).status_code == 429
    assert anonymous.get("/users/me", headers=headers(another_user_token)).status_code == 200


def test_cors_preflight_and_rejected_origin(anonymous):
    request_headers = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Content-Type, Authorization, X-Correlation-ID"}
    response = anonymous.options("/loans", headers=request_headers)
    assert response.status_code == 200
    assert response.headers["Access-Control-Allow-Origin"] == request_headers["Origin"]
    assert response.headers["Access-Control-Allow-Credentials"] == "true"
    assert "X-Correlation-ID" in response.headers
    for change in [{"Origin": "https://untrusted.example"}, {"Access-Control-Request-Method": "TRACE"}, {"Access-Control-Request-Headers": "X-Not-Allowed"}]:
        denied = anonymous.options("/loans", headers={**request_headers, **change})
        assert denied.status_code == 400
    untrusted = anonymous.get("/", headers={"Origin": "https://untrusted.example"})
    assert "Access-Control-Allow-Origin" not in untrusted.headers


def test_middleware_headers_logging_and_errors(anonymous, security_app, caplog):
    @security_app.get("/test-unhandled")
    def failure():
        raise RuntimeError("DO-NOT-LOG-THIS-SECRET")
    with caplog.at_level(logging.INFO, logger="device_systems.requests"):
        response = anonymous.get("/test-unhandled?password=DO-NOT-LOG-THIS-SECRET", headers={"Origin": "http://localhost:5173", "X-Correlation-ID": "test-correlation-123", "Authorization": "Bearer DO-NOT-LOG-THIS-SECRET"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Error interno del servidor"}
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:5173"
    assert response.headers["X-Correlation-ID"] == "test-correlation-123"
    assert float(response.headers["X-Process-Time-Ms"]) >= 0
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    app_logs = " ".join(record.getMessage() for record in caplog.records if record.name.startswith("device_systems"))
    assert "DO-NOT-LOG-THIS-SECRET" not in app_logs
    assert "status=500" in app_logs and "test-correlation-123" in app_logs


def test_security_headers_host_gzip_and_https(anonymous, security_app):
    response = anonymous.get("/", headers={"X-Correlation-ID": "x" * 100})
    assert len(response.headers["X-Correlation-ID"]) == 36
    assert "Strict-Transport-Security" not in response.headers
    assert anonymous.get("/", headers={"Host": "untrusted.example"}).status_code == 400
    assert anonymous.get("/openapi.json", headers={"Accept-Encoding": "gzip"}).headers["Content-Encoding"] == "gzip"
    with TestClient(security_app, base_url="https://testserver") as https_client:
        assert "Strict-Transport-Security" in https_client.get("/").headers


@pytest.mark.parametrize("overrides", [{"secret_key": "short"}, {"allowed_origins": ["*"]}, {"allowed_origins": ["https://example.com/path"]}, {"environment": "production"}, {"allowed_hosts": ["*"]}, {"access_token_expire_minutes": 0}])
def test_invalid_settings(overrides):
    with pytest.raises(ValidationError):
        Settings.model_validate({"secret_key": "testing-secret-of-at-least-32-characters", **overrides})


def test_https_redirect():
    settings = SETTINGS.model_copy(update={"https_redirect": True})
    with TestClient(create_app(settings), follow_redirects=False) as client:
        response = client.get("/")
        assert response.status_code == 307
        assert response.headers["Location"].startswith("https://")


def test_admin_creates_password_and_revoked_role_takes_effect(anonymous, database):
    register(anonymous)
    token = login(anonymous).json()["access_token"]
    with Session(database) as db:
        db.get(User, 1).role = "admin"
        db.commit()
    response = anonymous.post("/users", headers=headers(token), json={"name": "Nuevo Usuario", "email": "new@example.com", "password": PASSWORD})
    assert response.status_code == 201
    assert "password" not in response.json() and "hashed_password" not in response.json()
    assert login(anonymous, "new@example.com").status_code == 200
    assert anonymous.patch("/users/2", headers=headers(token), json={"name": None}).status_code == 422
    assert anonymous.patch("/users/2", headers=headers(token), json={"name": "  "}).status_code == 422
    with Session(database) as db:
        db.get(User, 1).role = "user"
        db.commit()
    assert anonymous.get("/users", headers=headers(token)).status_code == 403


def test_register_rate_limit(anonymous):
    for index in range(5):
        assert register(anonymous, f"user{index}@example.com").status_code == 201
    response = register(anonymous, "last@example.com")
    assert response.status_code == 429
    assert "Retry-After" in response.headers


def test_database_failure_has_cors_and_security_headers(anonymous, database):
    from sqlalchemy import text
    with database.begin() as connection:
        connection.execute(text("DROP TABLE loans"))
        connection.execute(text("DROP TABLE users"))
    response = anonymous.post("/token", data={"username": "ana@example.com", "password": PASSWORD}, headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 500
    assert response.json() == {"detail": "Error interno de base de datos"}
    assert response.headers["Access-Control-Allow-Origin"] == "http://localhost:3000"
    assert response.headers["X-Frame-Options"] == "DENY"
