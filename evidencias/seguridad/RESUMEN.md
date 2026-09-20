# Resumen de la última actividad

## Parte 1. Autenticación y persistencia

- Passlib 1.7.4 con bcrypt 4.0.1 y 12 rondas.
- Funciones centralizadas de hash/verificación, salt aleatorio y rechazo de truncamiento a 72 bytes.
- Migración Alembic `0003_user_password`; conserva usuarios y préstamos anteriores.
- Registro público, token OAuth2 mediante formulario y perfil `/users/me`.
- JWT firmado HS256, con vencimiento, sujeto, emisor y audiencia validados.
- Usuarios activos y permisos consultados en la base; registro público sin elevación de rol.
- Utilidad local para crear administrador y asignar contraseñas sin mostrar ni guardar texto plano.

## Parte 2. Middlewares y CORS

- Middleware de clase con BaseHTTPMiddleware para tiempo, logs e ID de correlación.
- Decoradores HTTP para cabeceras globales y tratamiento seguro de errores inesperados.
- Cabeceras nosniff, DENY y Referrer-Policy; HSTS cuando la petición es HTTPS.
- CORS configurable por entorno con orígenes explícitos, métodos y cabeceras enumerados.
- Preflight OPTIONS público, cabeceras expuestas al frontend y CORS presente en errores.
- GZip, validación de Host y redirección HTTPS opcional.

## Parte 3. Validación y límites

- Pydantic v2: ConfigDict, field_validator, model_validator, SecretStr y from_attributes.
- Normalización de nombre/email y distinción entre nulo explícito y ausencia en PATCH.
- Respuestas de validación sin repetir entradas privadas.
- SlowAPI con ventanas móviles: registro/login 5 por minuto por IP y perfil 30 por minuto por usuario verificado.
- Respuesta 429 con Retry-After; distintos tokens del mismo usuario comparten el límite.

## Parte 4. Pruebas, documentación y evidencias

**85 pruebas aprobadas; 0 fallos; duración 91.27 segundos.**

La suite cubre funcionalidad anterior, hashes, registro/login, tokens inválidos/vencidos, campos privados, usuarios inactivos, permisos, CORS, middleware, rate limiting y migraciones con conservación de datos.

Las cinco advertencias proceden de dependencias: Starlette/httpx, AnyIO y el uso de una función de asyncio deprecada dentro de SlowAPI. No impiden la ejecución.

Se generaron 15 capturas: Swagger, el formulario OAuth2 y 13 peticiones/respuestas. Las evidencias utilizan una base temporal y redactan contraseñas y tokens. El README y `docs/SEGURIDAD.md` explican la instalación, el orden de middleware, las variables, las rutas y los comandos de administración.

Las pruebas de regresión autorizan un administrador simulado para aislar las reglas de negocio anteriores. Las pruebas de seguridad usan el registro, login y JWT reales sin sustituir la dependencia de autenticación.

Se trabaja en la rama local `device_systems_seguridad`. No se realizó push. Las eliminaciones antiguas de `pruebas/` permanecen fuera de los cambios de esta actividad.

## Límites documentados

- No hay refresh tokens ni lista de revocación: los JWT expiran según su duración configurada. Desactivar un usuario sí bloquea inmediatamente el acceso; cambiar contraseña no revoca tokens anteriores.
- El almacenamiento local de SlowAPI es por proceso; un despliegue con varios workers necesita un backend compartido.
- La configuración y las pruebas están orientadas a SQLite y Python 3.14 en Windows.
