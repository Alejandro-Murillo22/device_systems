"""
device_systems - API REST para Gestión de Usuarios (v2.0)
Punto de entrada principal de la aplicación FastAPI.

Ejecutar con:
    uvicorn app.main:app --reload
"""

from fastapi import Depends, FastAPI, Request
from fastapi.responses import JSONResponse

from app.dependencies.user_dependencies import get_api_settings
from app.routes import user_routes

app = FastAPI(
    title="device_systems API",
    description=(
        "API REST para la gestión de usuarios del sistema device_systems. "
        "Incluye CRUD completo (GET, POST, PUT, PATCH, DELETE), manejo "
        "profesional de errores y Dependency Injection con Depends()."
    ),
    version="2.0.0",
    contact={"name": "Alejandro Murillo", "email": "alejandro@device-systems.com"},
    openapi_tags=[
        {"name": "Users", "description": "Operaciones CRUD sobre el recurso usuarios."},
        {"name": "Root", "description": "Estado general de la API."},
    ],
)


@app.middleware("http")
async def add_custom_headers(request: Request, call_next):
    """
    Agrega cabeceras HTTP personalizadas a TODAS las respuestas, incluidas
    las de error (404, 400, 401, 422), porque se ejecuta después de
    `call_next` sin importar si el endpoint tuvo éxito o falló.
    """
    response = await call_next(request)
    response.headers["X-App-Name"] = "device_systems"
    response.headers["X-API-Version"] = "2.0"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Red de seguridad ante errores no controlados explícitamente."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error interno no controlado: {str(exc)}"},
    )


@app.get("/", tags=["Root"], summary="Estado de la API")
def root(settings: dict = Depends(get_api_settings)):
    """
    Endpoint raíz de verificación rápida. Usa Depends(get_api_settings)
    para no repetir el nombre/versión de la app como texto suelto aquí.
    """
    return {
        "app": settings["app_name"],
        "version": settings["version"],
        "status": "ok",
        "docs": "/docs",
        "redoc": "/redoc",
    }


app.include_router(user_routes.router)
