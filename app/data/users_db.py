"""
Capa de datos (simulación de base de datos en memoria) para device_systems.

Se separa en su propio módulo para que tanto las rutas, los servicios y las
dependencias puedan acceder a los mismos datos sin depender unas de otras
directamente (evita import circular entre routes y services).
"""

from app.schemas.user_schema import UserInDB, UserRole


users_db: dict[int, UserInDB] = {
    1: UserInDB(
        id=1,
        name="Alejandro Murillo",
        email="alejandro@device-systems.com",
        role=UserRole.ADMIN,
        is_active=True,
    ),
    2: UserInDB(
        id=2,
        name="Santiago Zapata",
        email="juan@device-systems.com",
        role=UserRole.SUPPORT,
        is_active=True,
    ),
    3: UserInDB(
        id=3,
        name="Juan Rojas",
        email="juan@device-systems.com",
        role=UserRole.USER,
        is_active=False,
    ),
}

_next_id = 4


def get_next_id() -> int:
    """
    Devuelve el siguiente ID disponible y avanza el contador interno.

    Se encapsula en una función (en vez de exponer `_next_id` directamente)
    para que el incremento sea atómico dentro de este módulo y nadie desde
    afuera pueda "olvidarse" de sumarle 1 después de usarlo.
    """
    global _next_id
    current = _next_id
    _next_id += 1
    return current
