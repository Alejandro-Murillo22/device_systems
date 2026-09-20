import os
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address
from fastapi import Request
from fastapi.responses import JSONResponse

# Un solo Limiter; moving-window usa ventanas móviles reales.
limiter = Limiter(key_func=get_remote_address, headers_enabled=True,
                  storage_uri=os.getenv("RATE_LIMIT_STORAGE_URI", "memory://"), strategy="moving-window")


def authenticated_user_key(request: Request) -> str:
    user_id = getattr(request.state, "user_id", None)
    return f"user:{user_id}" if user_id is not None else f"ip:{get_remote_address(request)}"


def rate_limit_handler(request: Request, exc: RateLimitExceeded):
    original = _rate_limit_exceeded_handler(request, exc)
    headers = {key: value for key, value in original.headers.items() if key.lower() not in {"content-length", "content-type"}}
    return JSONResponse(status_code=429, content={"detail": "Límite de peticiones excedido"}, headers=headers)
