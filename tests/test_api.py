import pytest
from sqlalchemy import text


def borrow(client, records):
    user, device = records
    return client.post("/loans", json={"user_id": user["id"], "device_id": device["id"]})


def test_complete_loan_lifecycle(client, records):
    user, device = records
    response = borrow(client, records)
    assert response.status_code == 201
    loan = response.json()
    assert loan["status"] == "active" and loan["return_date"] is None
    assert client.get(f'/devices/{device["id"]}').json()["is_available"] is False
    assert borrow(client, records).status_code == 409
    for path in ["/loans/details", "/loans?status=active", "/loans?device_type=laptop", f'/users/{user["id"]}/loans', f'/devices/{device["id"]}/loans']:
        result = client.get(path)
        assert result.status_code == 200
        assert len(result.json()) == 1
        assert result.json()[0]["user"]["email"] == user["email"]
        assert result.json()[0]["device"]["serial_number"] == device["serial_number"]
        assert "internal_notes" not in result.json()[0]["user"]
    assert len(client.get(f'/users/{user["id"]}/devices').json()) == 1
    returned = client.patch(f'/loans/{loan["id"]}/return')
    assert returned.status_code == 200
    assert returned.json()["status"] == "returned"
    assert returned.json()["return_date"] is not None
    assert client.get(f'/devices/{device["id"]}').json()["is_available"] is True
    assert client.get(f'/users/{user["id"]}/devices').json() == []
    assert client.patch(f'/loans/{loan["id"]}/return').status_code == 409
    assert borrow(client, records).status_code == 201
    assert len(client.get(f'/devices/{device["id"]}/loans').json()) == 2


@pytest.mark.parametrize("path", ["/users/999/loans", "/users/999/devices", "/devices/999", "/devices/999/loans", "/loans/999"])
def test_missing_resources(client, path):
    assert client.get(path).status_code == 404


def test_missing_loan_references(client, records):
    user, device = records
    assert client.post("/loans", json={"user_id": 999, "device_id": device["id"]}).status_code == 404
    assert client.post("/loans", json={"user_id": user["id"], "device_id": 999}).status_code == 404
    assert client.patch("/loans/999/return").status_code == 404
    assert client.get(f'/devices/{device["id"]}').json()["is_available"] is True


@pytest.mark.parametrize("query", ["status=invalid", "user_id=0", "device_id=-1", "user_email=invalid", "date_from=invalid", "date_from=2026-10-01&date_to=2026-01-01", "search=", "device_type="])
def test_invalid_loan_filters(client, query):
    assert client.get("/loans?" + query).status_code == 422


def test_combined_filters(client, records):
    borrow(client, records)
    for query in ["status=active&device_type=laptop&user_email=ana@example.com", "search=ANA", "search=Think", "date_from=2000-01-01T00:00:00Z&date_to=2100-01-01T00:00:00%2B00:00", "user_id=1&device_id=1"]:
        assert len(client.get("/loans?" + query).json()) == 1
    for query in ["status=returned", "device_type=tablet", "search=missing", "search=%25", "date_to=2000-01-01"]:
        assert client.get("/loans?" + query).json() == []


def test_device_crud_and_filters(client, records):
    _, device = records
    path = f'/devices/{device["id"]}'
    assert client.post("/devices", json={k: device[k] for k in ["name", "serial_number", "device_type"]}).status_code == 400
    for query in ["device_type=laptop", "is_available=true", "brand=lenovo", "search=THINK", "brand=lenovo&is_available=true&device_type=laptop"]:
        assert len(client.get("/devices?" + query).json()) == 1
    assert client.get("/devices?is_available=invalid").status_code == 422
    assert client.get("/devices?is_available=false").json() == []
    assert client.patch(path, json={}).status_code == 400
    assert client.patch(path, json={"name": None}).status_code == 422
    assert client.patch(path, json={"brand": None}).status_code == 200
    assert client.put(path, json={"name": "Monitor", "serial_number": "MON-002", "device_type": "monitor", "is_available": True}).status_code == 200
    assert client.get(path).json()["brand"] is None
    assert client.put(path, json={"name": "Monitor"}).status_code == 422
    response = client.delete(path)
    assert response.status_code == 204 and response.content == b""
    assert client.get(path).status_code == 404


def test_history_and_availability_protected(client, records):
    user, device = records
    loan = borrow(client, records).json()
    assert client.patch(f'/devices/{device["id"]}', json={"is_available": True}).status_code == 409
    for _ in range(2):
        assert client.delete(f'/devices/{device["id"]}').status_code == 409
        assert client.delete(f'/users/{user["id"]}', headers={"X-API-Key": "test-key"}).status_code == 409
        client.patch(f'/loans/{loan["id"]}/return')


@pytest.mark.parametrize("payload", [{}, {"name": " ", "serial_number": "A", "device_type": "laptop"}, {"name": "Laptop", "serial_number": " ", "device_type": "laptop"}, {"name": "Laptop", "serial_number": "A", "device_type": ""}])
def test_invalid_devices(client, payload):
    assert client.post("/devices", json=payload).status_code == 422


def test_users_regression(client, records):
    user, _ = records
    path = f'/users/{user["id"]}'
    assert client.post("/users", json={"name": "Otra Ana", "email": "ANA@example.com"}).status_code == 400
    assert client.post("/users", json={"name": "A", "email": "bad"}).status_code == 422
    assert client.patch(path, json={}).status_code == 400
    assert client.put(path, json={"name": "Ana"}).status_code == 422
    assert client.put(path, json={"name": "Ana Nueva", "email": "ana@example.com", "role": "support", "is_active": False}).status_code == 200
    assert client.get("/users?role=support&is_active=false").json()["total"] == 1
    assert client.patch(path, json={"is_active": True}).status_code == 200
    assert client.delete(path).status_code == 401
    assert client.delete(path, headers={"X-API-Key": "bad"}).status_code == 401
    assert client.delete(path, headers={"X-API-Key": "test-key"}).status_code == 204


def test_docs(client):
    for path in ["/docs", "/redoc", "/openapi.json"]:
        assert client.get(path).status_code == 200
    schema = client.get("/openapi.json").json()
    assert {"Users", "Devices", "Loans"} <= {tag["name"] for tag in schema["tags"]}
    assert "/loans/details" in schema["paths"]


def test_database_error_does_not_leak_sql(client, database):
    with database.begin() as connection:
        connection.execute(text("DROP TABLE loans"))
    response = client.get("/loans")
    assert response.status_code == 500
    assert response.json() == {"detail": "Error interno de base de datos"}


def test_duplicate_device_update_preserves_data(client, records):
    response = client.post("/devices", json={"name": "Tablet", "serial_number": "TAB-001", "device_type": "tablet"})
    path = f'/devices/{response.json()["id"]}'
    assert client.patch(path, json={"serial_number": "LEN-001"}).status_code == 400
    assert client.get(path).json()["serial_number"] == "TAB-001"


@pytest.mark.parametrize("payload", [{"user_id": 0, "device_id": 1}, {"user_id": 1}, {"user_id": 1, "device_id": 1, "status": "returned"}])
def test_invalid_loan_payload(client, payload):
    assert client.post("/loans", json=payload).status_code == 422
