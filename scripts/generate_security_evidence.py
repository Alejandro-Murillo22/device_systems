"""Evidencias de seguridad sobre una base temporal, con secretos redactados."""
import argparse
from datetime import timedelta
import html
import io
import json
import logging
import os
from pathlib import Path
import secrets
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidencias" / "seguridad"


def redact(value):
    if isinstance(value, dict):
        return {key: "[REDACTADO]" if key in {"password", "access_token", "Authorization", "hashed_password"} else redact(item) for key, item in value.items()}
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="device-security-") as temporary:
        database = Path(temporary) / "security.db"
        env = {**os.environ, "DATABASE_URL": f"sqlite:///{database.as_posix()}",
               "SECRET_KEY": secrets.token_urlsafe(48), "API_VERSION": "5.0.0",
               "ENVIRONMENT": "development", "HTTPS_REDIRECT": "false",
               "ALLOWED_ORIGINS": '["http://localhost:5173"]',
               "ALLOWED_HOSTS": '["testserver","localhost","127.0.0.1"]',
               "RATE_LIMIT_STORAGE_URI": "memory://", "PYTHONIOENCODING": "utf-8"}
        logs = []
        for command in [("upgrade", "head"), ("history",), ("check",)]:
            result = subprocess.run([sys.executable, "-m", "alembic", *command], cwd=ROOT, env=env, capture_output=True, text=True, encoding="utf-8")
            logs.append(f"$ python -m alembic {' '.join(command)}\n{result.stdout}{result.stderr}")
            if result.returncode:
                raise RuntimeError(result.stderr)
        (OUT / "alembic.txt").write_text("\n".join(logs), encoding="utf-8")
        os.environ.update(env)
        sys.path.insert(0, str(ROOT))
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database.database import engine
        from app.security import create_access_token

        logging.getLogger("httpx").setLevel(logging.WARNING)
        request_log = io.StringIO()
        handler = logging.StreamHandler(request_log)
        logger = logging.getLogger("device_systems.requests")
        logger.addHandler(handler)
        logger.propagate = False
        results = []
        password = secrets.token_urlsafe(18)
        with TestClient(app, raise_server_exceptions=False) as client:
            def record(label, method, path, expected, **kwargs):
                response = client.request(method, path, **kwargs)
                assert response.status_code == expected, (path, response.status_code, response.text)
                try:
                    body = response.json()
                except ValueError:
                    body = response.text
                results.append({"label": label, "method": method, "path": path,
                                "request": redact(kwargs), "status": response.status_code,
                                "headers": dict(response.headers), "response": redact(body)})
                return response

            payload = {"name": "Ana Perez", "email": "ana@example.com", "password": password}
            record("01-registro", "POST", "/register", 201, json=payload)
            record("02-duplicado", "POST", "/register", 400, json=payload)
            token = record("03-login", "POST", "/token", 200, data={"username": "ana@example.com", "password": password}).json()["access_token"]
            auth = {"Authorization": f"Bearer {token}"}
            record("04-perfil", "GET", "/users/me", 200, headers=auth)
            record("05-sin-token", "GET", "/devices", 401)
            record("06-token-invalido", "GET", "/users/me", 401, headers={"Authorization": "Bearer token-modificado"})
            expired = create_access_token(1, expires_delta=timedelta(seconds=-60))
            record("07-token-expirado", "GET", "/users/me", 401, headers={"Authorization": f"Bearer {expired}"})
            record("08-permisos", "GET", "/users", 403, headers=auth)
            record("09-middleware", "GET", "/", 200, headers={"X-Correlation-ID": "evidencia-ultima-actividad"})
            preflight = {"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "Authorization,Content-Type"}
            record("10-cors-permitido", "OPTIONS", "/loans", 200, headers=preflight)
            record("11-cors-rechazado", "OPTIONS", "/loans", 400, headers={**preflight, "Origin": "https://no-autorizado.example"})
            for _ in range(4):
                assert client.post("/token", data={"username": "ana@example.com", "password": "incorrecta"}).status_code == 401
            record("12-rate-limit", "POST", "/token", 429, data={"username": "ana@example.com", "password": "incorrecta"}, headers={"Origin": "http://localhost:5173"})
            record("13-validacion", "POST", "/register", 422, json={**payload, "password": "abc"})
            (OUT / "openapi.json").write_text(json.dumps(client.get("/openapi.json").json(), ensure_ascii=False, indent=2), encoding="utf-8")
        (OUT / "api.json").write_text(json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.removeHandler(handler)
        logger.propagate = True
        (OUT / "requests.log").write_text(request_log.getvalue(), encoding="utf-8")

        if args.screenshots:
            from playwright.sync_api import sync_playwright
            with socket.socket() as sock:
                sock.bind(("127.0.0.1", 0))
                port = sock.getsockname()[1]
            with (OUT / "server.log").open("w", encoding="utf-8") as log:
                process = subprocess.Popen([sys.executable, "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", str(port)], cwd=ROOT, env=env, stdout=log, stderr=log)
                try:
                    for _ in range(100):
                        try:
                            urllib.request.urlopen(f"http://127.0.0.1:{port}/", timeout=1)
                            break
                        except OSError:
                            time.sleep(0.1)
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch(channel="msedge", headless=True)
                        page = browser.new_page(viewport={"width": 1360, "height": 1000})
                        page.goto(f"http://127.0.0.1:{port}/docs")
                        page.wait_for_selector(".opblock", timeout=60000)
                        page.screenshot(path=str(OUT / "swagger.png"), full_page=True)
                        page.locator(".auth-wrapper .authorize").click()
                        page.wait_for_selector(".dialog-ux")
                        page.screenshot(path=str(OUT / "oauth2.png"))
                        for result in results:
                            content = json.dumps(result, ensure_ascii=False, indent=2)
                            page.set_content('<html lang="es"><meta charset="utf-8"><body style="background:#13202c;color:#edf4fb;padding:28px;font:16px monospace"><h2>'+html.escape(result["label"])+'</h2><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+html.escape(content)+'</pre></body></html>')
                            page.screenshot(path=str(OUT / (result["label"] + ".png")), full_page=True)
                        browser.close()
                finally:
                    process.terminate()
                    process.wait(timeout=10)
        engine.dispose()
    print(f"Evidencias guardadas en {OUT}; contraseñas y tokens redactados.")


if __name__ == "__main__":
    main()
