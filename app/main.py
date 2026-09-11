import logging
from dotenv import load_dotenv

load_dotenv()

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError

from app.database.database import Base, engine
from app.dependencies.user_dependencies import get_api_settings
from app.routes import user_routes

logging.basicConfig(level=logging.INFO)

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="device_systems API",
    description=(
        "API REST para la gestión de usuarios de device_systems. "
        "Utiliza FastAPI, Pydantic v2 y SQLAlchemy para persistencia "
        "relacional, CRUD completo, filtros, validaciones, constraints "
        "y manejo controlado de errores."
    ),
    version="3.0.0",
    contact={"name": "Nombre Apellido", "email": "ejemplo@device-systems.com"},
    openapi_tags=[
        {"name": "Users", "description": "Operaciones CRUD sobre usuarios."},
        {"name": "Root", "description": "Estado general de la API."},
    ],
)


@app.middleware("http")
async def add_custom_headers(request: Request, call_next):
    """Agrega cabeceras HTTP personalizadas a todas las respuestas."""
    response = await call_next(request)
    response.headers["X-App-Name"] = "device_systems"
    response.headers["X-API-Version"] = "3.0"
    return response


@app.exception_handler(SQLAlchemyError)
async def database_exception_handler(request: Request, exc: SQLAlchemyError):
    logging.exception("Error de base de datos", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno de base de datos"},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Red de seguridad ante errores no controlados explícitamente."""
    logging.exception("Error interno no controlado", exc_info=exc)
    return JSONResponse(
        status_code=500,
        content={"detail": "Error interno del servidor"},
    )


@app.get("/", tags=["Root"], summary="Estado de la API")
def root(settings: dict = Depends(get_api_settings)):
    """Endpoint raíz de verificación rápida."""
    return {
        "app": settings["app_name"],
        "version": settings["version"],
        "status": "ok",
        "database": "sqlite + sqlalchemy",
        "docs": "/docs",
        "redoc": "/redoc",
    }


app.include_router(user_routes.router)