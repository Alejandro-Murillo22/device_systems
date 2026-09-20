"""Funciones transversales; la autenticación permanece en Depends()."""
import logging
import re
import time
import uuid

from fastapi import Request
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.gzip import GZipMiddleware
from starlette.middleware.httpsredirect import HTTPSRedirectMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from app.config import Settings

logger = logging.getLogger("device_systems.requests")
SAFE_ID = re.compile(r"[A-Za-z0-9._-]{1,64}\Z")


class RequestContextMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        provided = request.headers.get("X-Correlation-ID", "")
        request.state.correlation_id = provided if SAFE_ID.fullmatch(provided) else str(uuid.uuid4())
        start = time.perf_counter()
        response = await call_next(request)
        duration_ms = (time.perf_counter() - start) * 1000
        response.headers["X-Process-Time-Ms"] = f"{duration_ms:.2f}"
        response.headers["X-Correlation-ID"] = request.state.correlation_id
        # No guardar cuerpo, query string, Authorization, cookies ni credenciales.
        logger.info("method=%s path=%r status=%d duration_ms=%.2f ip=%s correlation_id=%s",
                    request.method, request.url.path, response.status_code, duration_ms,
                    request.client.host if request.client else "unknown", request.state.correlation_id)
        return response


def configure_middleware(app, settings: Settings):
    # Primera capa añadida = más interna. Convierte errores no controlados antes de CORS.
    @app.middleware("http")
    async def error_boundary(request: Request, call_next):
        try:
            return await call_next(request)
        except Exception as exc:
            logger.error("Unhandled error type=%s correlation_id=%s", type(exc).__name__, getattr(request.state, "correlation_id", "unknown"))
            return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})

    if settings.https_redirect:
        app.add_middleware(HTTPSRedirectMiddleware)
    app.add_middleware(TrustedHostMiddleware, allowed_hosts=settings.allowed_hosts)
    app.add_middleware(GZipMiddleware, minimum_size=1000)
    app.add_middleware(CORSMiddleware, allow_origins=settings.allowed_origins,
                       allow_credentials=True,
                       allow_methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS"],
                       allow_headers=["Authorization", "Content-Type", "X-API-Key", "X-Correlation-ID", "X-Requested-With"],
                       expose_headers=["X-Process-Time-Ms", "X-Correlation-ID", "X-App-Name", "X-API-Version", "Retry-After", "X-RateLimit-Limit", "X-RateLimit-Remaining", "X-RateLimit-Reset"],
                       max_age=600)
    app.add_middleware(RequestContextMiddleware)

    # Última capa añadida = más externa, incluye errores y preflights.
    @app.middleware("http")
    async def security_headers(request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["Referrer-Policy"] = "no-referrer"
        response.headers["X-App-Name"] = "device_systems"
        response.headers["X-API-Version"] = settings.api_version
        if request.url.scheme == "https":
            response.headers["Strict-Transport-Security"] = "max-age=31536000"
        return response
