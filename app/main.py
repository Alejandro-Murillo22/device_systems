import logging

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from slowapi.errors import RateLimitExceeded
from sqlalchemy.exc import SQLAlchemyError

from app.config import Settings, get_settings
from app.middleware import configure_middleware
from app.rate_limit import limiter, rate_limit_handler
from app.routes import auth_routes, device_routes, loan_routes, user_routes

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("device_systems.errors")


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    application = FastAPI(
        title="device_systems API", version=settings.api_version,
        description="API de usuarios, dispositivos y préstamos con Alembic, OAuth2/JWT, Passlib bcrypt, middlewares, CORS y rate limiting.",
        openapi_tags=[
            {"name": "Auth", "description": "Registro, token OAuth2 y perfil autenticado."},
            {"name": "Users", "description": "Usuarios: administración y consultas propias."},
            {"name": "Devices", "description": "Inventario y disponibilidad de equipos."},
            {"name": "Loans", "description": "Préstamos, devoluciones y consultas relacionadas."},
            {"name": "Root", "description": "Estado general de la API."},
        ],
    )
    application.state.settings = settings
    application.state.limiter = limiter
    application.add_exception_handler(RateLimitExceeded, rate_limit_handler)

    @application.exception_handler(SQLAlchemyError)
    async def database_error(request: Request, exc: SQLAlchemyError):
        # Los mensajes SQL pueden contener parámetros privados: registrar solo el tipo.
        logger.error("Database error type=%s correlation_id=%s", type(exc).__name__, getattr(request.state, "correlation_id", "unknown"))
        return JSONResponse(status_code=500, content={"detail": "Error interno de base de datos"})

    @application.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError):
        # Evitar que un 422 repita contraseñas u otros datos de entrada.
        errors = [{"loc": item["loc"], "msg": item["msg"], "type": item["type"]} for item in exc.errors()]
        return JSONResponse(status_code=422, content={"detail": errors})

    @application.get("/", tags=["Root"], summary="Estado de la API")
    def root():
        return {"app": "device_systems", "version": settings.api_version, "status": "ok",
                "database": "sqlite + sqlalchemy", "docs": "/docs", "redoc": "/redoc"}

    # /users/me debe registrarse antes de /users/{user_id}.
    application.include_router(auth_routes.router)
    application.include_router(user_routes.router)
    application.include_router(device_routes.router)
    application.include_router(loan_routes.router)
    configure_middleware(application, settings)
    return application


app = create_app()
