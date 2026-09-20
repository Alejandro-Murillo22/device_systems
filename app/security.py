"""Hash bcrypt y tokens JWT firmados; nunca serializar contraseñas o hashes."""
from datetime import datetime, timedelta, timezone
from functools import lru_cache
import secrets

from jose import jwt
from passlib.context import CryptContext

from app.config import Settings, get_settings

ALGORITHM = "HS256"
ISSUER = "device_systems"
AUDIENCE = "device_systems_api"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto", bcrypt__rounds=12, bcrypt__truncate_error=True)


def validate_password_size(password: str) -> str:
    # Bcrypt opera sobre bytes, no sobre caracteres Unicode.
    if not 8 <= len(password) or len(password.encode("utf-8")) > 72 or "\x00" in password:
        raise ValueError("La contraseña requiere al menos 8 caracteres, máximo 72 bytes UTF-8 y ningún carácter nulo")
    return password


def hash_password(password: str) -> str:
    return pwd_context.hash(validate_password_size(password))


def verify_password(plain_password: str, hashed_password: str) -> bool:
    if len(plain_password.encode("utf-8")) > 72 or "\x00" in plain_password:
        return False
    try:
        return pwd_context.verify(plain_password, hashed_password)
    except (ValueError, TypeError):
        return False


@lru_cache
def dummy_password_hash() -> str:
    """Verificación equivalente para cuentas desconocidas o sin contraseña."""
    return hash_password(secrets.token_urlsafe(32))


def create_access_token(user_id: int, settings: Settings | None = None, expires_delta: timedelta | None = None) -> str:
    settings = settings or get_settings()
    now = datetime.now(timezone.utc)
    expiration = now + (expires_delta if expires_delta is not None else timedelta(minutes=settings.access_token_expire_minutes))
    return jwt.encode({"sub": str(user_id), "iat": now, "exp": expiration,
                       "iss": ISSUER, "aud": AUDIENCE, "jti": secrets.token_urlsafe(16)},
                      settings.secret_key.get_secret_value(), algorithm=ALGORITHM)


def decode_access_token(token: str, settings: Settings | None = None) -> int:
    settings = settings or get_settings()
    payload = jwt.decode(token, settings.secret_key.get_secret_value(), algorithms=[ALGORITHM],
                         issuer=ISSUER, audience=AUDIENCE,
                         options={"require_exp": True, "require_sub": True, "require_iat": True, "require_iss": True, "require_aud": True})
    subject = payload["sub"]
    if not isinstance(subject, str) or not subject.isascii() or not subject.isdecimal() or len(subject) > 19 or not 0 < int(subject) <= 2**63 - 1:
        raise ValueError("Identificador de usuario inválido")
    return int(subject)
