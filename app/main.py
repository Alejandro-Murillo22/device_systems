"""
device_systems - API REST para Gestión de Usuarios
Punto de entrada principal de la aplicación FastAPI.

Ejecutar con:
    uvicorn app.main:app --reload
"""

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.routes import user_routes

app = FastAPI(
    title="device_systems",
    description=(
        "API REST para la gestión del recurso **users** dentro del sistema "
        "device_systems. Construida con FastAPI y Pydantic v2 como parte de "
        "la actividad 'Fundamentos de FastAPI'."
    ),
    version="1.0.0",
    contact={"name": "device_systems"},
)


@app.middleware("http")
async def add_custom_headers(request: Request, call_next):
    """
    Middleware que agrega cabeceras HTTP personalizadas a TODAS las
    respuestas de la API, tal como pide la Fase 5 de la guía:
        X-App-Name: device_systems
        X-API-Version: 1.0
    """
    response = await call_next(request)
    response.headers["X-App-Name"] = "device_systems"
    response.headers["X-API-Version"] = "1.0"
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    """Manejador genérico para evitar que errores inesperados tumben la API."""
    return JSONResponse(
        status_code=500,
        content={"detail": f"Error interno no controlado: {str(exc)}"},
    )


@app.get("/", tags=["Root"], summary="Estado de la API")
def root():
    """Endpoint raíz para verificar rápidamente que la API está en línea."""
    return {
        "app": "device_systems",
        "status": "ok",
        "docs": "/docs",
    }


app.include_router(user_routes.router)
