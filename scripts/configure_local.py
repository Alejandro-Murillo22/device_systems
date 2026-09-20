"""Prepara .env sin mostrar ni reemplazar claves existentes."""
from pathlib import Path
import secrets
from dotenv import dotenv_values, set_key

ROOT = Path(__file__).resolve().parents[1]
env_file = ROOT / ".env"
if not env_file.exists():
    env_file.write_text((ROOT / ".env.example").read_text(encoding="utf-8"), encoding="utf-8")
values = dotenv_values(env_file)
if not values.get("SECRET_KEY") or values["SECRET_KEY"] == "GENERAR_CON_CONFIGURE_LOCAL":
    set_key(str(env_file), "SECRET_KEY", secrets.token_urlsafe(48))
print("Configuración local lista en .env (clave privada no mostrada).")
