"""Genera evidencias reales en una base temporal; nunca modifica la base del usuario.

Ejecutar: python scripts/generate_evidence.py
Para capturas: pip install playwright; python scripts/generate_evidence.py --screenshots
"""
import argparse
import html
import json
import os
from pathlib import Path
import socket
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "evidencias"


def run(args, cwd, env):
    result = subprocess.run([sys.executable, "-m", "alembic", *args], cwd=cwd, env=env, capture_output=True, text=True)
    output = f"$ python -m alembic {' '.join(args)}\n{result.stdout}{result.stderr}\nexit_code={result.returncode}\n"
    if result.returncode:
        raise RuntimeError(output)
    return output


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--screenshots", action="store_true")
    args = parser.parse_args()
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="device-evidence-") as temporary:
        work = Path(temporary)
        database = work / "evidence.db"
        env = {**os.environ, "DATABASE_URL": f"sqlite:///{database.as_posix()}", "PYTHONPATH": str(ROOT), "PYTHONIOENCODING": "utf-8"}
        init = run(["init", "alembic"], work, env)
        (work / "alembic" / "env.py").write_text((ROOT / "alembic" / "env.py").read_text(encoding="utf-8"), encoding="utf-8")
        generated = run(["revision", "--autogenerate", "-m", "create users devices and loans tables"], work, env)
        applied = run(["upgrade", "head"], ROOT, env)
        applied += run(["history"], ROOT, env) + run(["current"], ROOT, env) + run(["check"], ROOT, env)
        (OUT / "alembic.txt").write_text(init + generated + applied, encoding="utf-8")
        with sqlite3.connect(database) as db:
            structure = "\n\n".join(row[0] for row in db.execute("SELECT sql FROM sqlite_master WHERE sql IS NOT NULL ORDER BY type, name"))
        db.close()
        structure = "\n".join(line.rstrip() for line in structure.splitlines()) + "\n"
        (OUT / "tables.sql").write_text(structure, encoding="utf-8")
        os.environ["DATABASE_URL"] = env["DATABASE_URL"]
        sys.path.insert(0, str(ROOT))
        from fastapi.testclient import TestClient
        from app.main import app
        from app.database.database import engine
        responses = []
        with TestClient(app) as client:
            def request(method, path, payload=None):
                response = client.request(method, path, json=payload) if payload is not None else client.request(method, path)
                responses.append({"method": method, "path": path, "request": payload, "status": response.status_code, "response": response.json()})
                return response
            assert request("POST", "/users", {"name": "Ana Perez", "email": "ana@example.com"}).status_code == 201
            assert request("POST", "/devices", {"name": "Lenovo ThinkPad", "serial_number": "LEN-001", "device_type": "laptop", "brand": "lenovo"}).status_code == 201
            assert request("POST", "/loans", {"user_id": 1, "device_id": 1}).status_code == 201
            assert request("POST", "/loans", {"user_id": 1, "device_id": 1}).status_code == 409
            request("GET", "/loans/details")
            request("GET", "/loans?status=active&device_type=laptop")
            request("GET", "/users/1/loans")
            assert request("PATCH", "/loans/1/return").status_code == 200
            assert request("GET", "/devices/1").json()["is_available"] is True
            request("GET", "/devices/1/loans")
            assert request("PATCH", "/loans/1/return").status_code == 409
            assert request("GET", "/loans?status=invalid").status_code == 422
            (OUT / "openapi.json").write_text(json.dumps(client.get("/openapi.json").json(), ensure_ascii=False, indent=2), encoding="utf-8")
        (OUT / "api.json").write_text(json.dumps(responses, ensure_ascii=False, indent=2), encoding="utf-8")
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
                            urllib.request.urlopen(f"http://127.0.0.1:{port}/openapi.json", timeout=1)
                            break
                        except OSError:
                            time.sleep(0.1)
                    with sync_playwright() as playwright:
                        browser = playwright.chromium.launch(channel="msedge", headless=True)
                        page = browser.new_page(viewport={"width": 1360, "height": 1000})
                        page.goto(f"http://127.0.0.1:{port}/docs")
                        page.wait_for_selector(".opblock", timeout=60000)
                        page.screenshot(path=str(OUT / "swagger.png"), full_page=True)
                        panels = {"01-init": init, "02-autogenerate": generated, "03-upgrade-history": applied, "04-tables": structure}
                        panels.update({f"api-{i+1:02d}": json.dumps(response, ensure_ascii=False, indent=2) for i, response in enumerate(responses)})
                        for name, content in panels.items():
                            page.set_content('<html lang="es"><meta charset="utf-8"><body style="background:#13202c;color:#edf4fb;padding:28px;font:16px monospace"><h2>Evidencia de ejecución: '+html.escape(name)+'</h2><pre style="white-space:pre-wrap;overflow-wrap:anywhere">'+html.escape(content)+'</pre></body></html>')
                            page.screenshot(path=str(OUT / f"{name}.png"), full_page=True)
                        browser.close()
                finally:
                    process.terminate()
                    process.wait(timeout=10)
        engine.dispose()
    print(f"Evidencias guardadas en {OUT}")


if __name__ == "__main__":
    main()
