# device_systems — Middleware, CORS y autenticación

API REST con FastAPI, SQLAlchemy 2, SQLite y Alembic para gestionar usuarios, dispositivos y préstamos. La versión **5.0.0** añade middleware, CORS, Pydantic v2, Passlib/bcrypt, OAuth2/JWT y rate limiting con SlowAPI al proyecto de la Guía 10.

**Documentación de la última actividad:** [seguridad, middlewares, CORS, permisos y pruebas](docs/SEGURIDAD.md). Las evidencias de la Guía 10 se conservan como registro histórico; las nuevas están en `evidencias/seguridad/`.

## 1. Instalación y ejecución

Desde la raíz del proyecto, con Python 3.11 o superior:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python scripts/configure_local.py
python -m alembic upgrade head
python -m app.manage create-admin --email admin@example.com --name "Administrador"
python -m uvicorn app.main:app --reload
```

En Linux/macOS, activar con `source .venv/bin/activate`. `configure_local.py` genera una clave privada en `.env` sin mostrarla ni reemplazar una ya existente. El comando de administración solicita la contraseña sin eco; solo se necesita una vez para crear el administrador.

- Swagger: http://127.0.0.1:8000/docs
- ReDoc: http://127.0.0.1:8000/redoc
- OpenAPI: http://127.0.0.1:8000/openapi.json
- Estado: http://127.0.0.1:8000/

La aplicación **no crea tablas al arrancar**: ejecutar primero las migraciones. La base se inicia sin datos de ejemplo. Los tests y las evidencias utilizan bases temporales independientes.

Configuración compartida por la API y Alembic, cargada desde `.env` en la raíz; las variables del entorno tienen prioridad:

```dotenv
DATABASE_URL=sqlite:///./device_systems.db
API_KEY=device_systems_key
API_VERSION=5.0.0
```

La API Key incluida es de demostración y se conserva para DELETE de usuarios, además del JWT y rol admin. `SECRET_KEY`, CORS y las demás opciones están en [.env.example](.env.example). `.env`, las bases locales y `.venv` están excluidos de Git. Esta entrega está implementada y probada con SQLite; el índice único parcial de préstamos abiertos utiliza su dialecto.

En Swagger, usar `POST /token` o **Authorize**: `username` es el email y `password` es la contraseña. Los recursos de negocio requieren JWT; `/register`, `/token`, `/` y la documentación son públicos. Las cuentas anteriores necesitan una contraseña mediante `python -m app.manage set-password --email correo@example.com`.

## 2. Trabajo dividido en partes

| Parte | Fases de la guía | Implementación |
|---|---|---|
| Persistencia | 1–6 | Proyecto anterior, configuración compartida, Alembic y relaciones User–Loan–Device |
| API y consultas | 7–10 | Schemas, CRUD de dispositivos, préstamos/devoluciones, joins y filtros |
| Validación | 11 y 13 | Errores HTTP, restricciones SQL, rollback y pruebas funcionales/concurrentes |
| Entrega | 12 y evidencias | Swagger/ReDoc, capturas, respuestas JSON y documentación |

```text
app/
  database/database.py         # Engine, Base, Session y PRAGMA foreign_keys
  models/                     # User, Device, Loan y relaciones
  schemas/                    # Entradas, actualizaciones y respuestas Pydantic
  services/                   # CRUD, transacciones y consultas SQLAlchemy
  dependencies/               # Sesión, usuario, filtros y clave de DELETE users
  routes/                     # Users, Devices y Loans
  main.py                     # API, routers y manejadores de errores
alembic/
  env.py                      # URL, modelos y Base.metadata
  versions/                   # Revisiones independientes del código del modelo
tests/                        # Pruebas sobre bases creadas mediante Alembic
scripts/generate_evidence.py  # Ejecuciones reproducibles y capturas
evidencias/                   # Resultados reales de la entrega
```

Se conserva `database.py` en lugar de renombrarlo a `connection.py`: la estructura de la guía es sugerida y así se preservan los imports existentes.

## 3. Migraciones con Alembic

Historial versionado:

```text
<base> -> 0001_users -> 0d0e8b654860 -> 0003_user_password (head)
```

- `0001_users`: tabla, índices y restricciones del modelo de usuarios anterior.
- `0d0e8b654860`: dispositivos, préstamos, claves foráneas y restricciones.
- `0003_user_password`: hash de contraseña nullable para conservar cuentas existentes sin asignarles una contraseña por defecto.

La migración se generó con `--autogenerate`, se revisó y se separó en dos revisiones para admitir bases anteriores. `alembic init alembic` se ejecuta una sola vez al configurar un proyecto; **no repetirlo al instalar este repositorio**.

```powershell
python -m alembic upgrade head
python -m alembic current
python -m alembic history
python -m alembic check
```

Para cambios futuros: modificar el modelo, ejecutar `python -m alembic revision --autogenerate -m "descripcion del cambio"`, revisar el script y aplicar `upgrade head`.

### Base anterior con usuarios, sin Alembic

1. Detener la API y respaldar el archivo SQLite.
2. Verificar que contiene la tabla `users` con **las mismas columnas, índices y constraints de `0001_users`**, sin `devices` ni `loans`.
3. Marcar únicamente esa revisión existente y aplicar las nuevas tablas:

```powershell
python -m alembic stamp 0001_users
python -m alembic upgrade head
python -m alembic check
```

`stamp` solo registra una versión: no crea ni comprueba tablas. No usar `stamp head` para ocultar errores ni aplicar el procedimiento a una estructura distinta. Hay pruebas de conservación de usuarios y adopción de una base sin versionar.

### Reversión y errores

`python -m alembic downgrade 0001_users` elimina préstamos y dispositivos y conserva usuarios. `downgrade base` elimina también usuarios. Utilizar reversiones destructivas únicamente en bases descartables o con respaldo.

Si una migración falla, revisar el error, `current`, `history`, la URL y el esquema real. SQLite no garantiza rollback de todo el DDL; corregir la causa o recuperar el respaldo antes de reintentar. Las pruebas verifican fallos por revisión inexistente y ruta de base inválida, además del ciclo upgrade/downgrade/upgrade y la coincidencia entre metadata y esquema.

## 4. Modelos y relaciones

```mermaid
erDiagram
    USERS ||--o{ LOANS : recibe
    DEVICES ||--o{ LOANS : registra
    USERS {
        int id PK
        string name
        string email UK
        string role
        boolean is_active
    }
    DEVICES {
        int id PK
        string name
        string serial_number UK
        string device_type
        string brand
        boolean is_available
        datetime created_at
    }
    LOANS {
        int id PK
        int user_id FK
        int device_id FK
        datetime loan_date
        datetime return_date
        string status
    }
```

`User.loans` y `Device.loans` se corresponden con `Loan.user` y `Loan.device` mediante `relationship()` y `back_populates`. La relación representa un historial: un equipo puede tener muchos préstamos, pero solo uno abierto (`active` o `overdue`).

- Usuario: restricciones anteriores de nombre, email único, rol y campos obligatorios; `internal_notes` permanece privado.
- Dispositivo: nombre, serie y tipo obligatorios, serie única, marca nullable, disponibilidad inicial `True`, fecha generada por la base.
- Préstamo: ambas claves foráneas obligatorias, estado válido y fechas coherentes; una devolución exige fecha, un préstamo abierto no la tiene.
- SQLite activa `PRAGMA foreign_keys=ON` por conexión. Las FK usan `RESTRICT` para conservar el historial.
- Un índice único parcial impide dos préstamos abiertos para el mismo equipo incluso ante accesos concurrentes.

Los timestamps se guardan en UTC sin offset en SQLite. Los filtros aceptan fechas ISO 8601, convierten offsets a UTC y consideran las fechas sin offset como UTC.

## 5. Endpoints

| Método | Ruta | Resultado |
|---|---|---|
| GET / POST | `/users` | Listar / crear usuarios |
| GET / PUT / PATCH / DELETE | `/users/{user_id}` | CRUD del usuario |
| GET | `/users/{user_id}/loans` | Historial con datos relacionados |
| GET | `/users/{user_id}/devices` | Equipos actualmente asignados |
| GET / POST | `/devices` | Listar / crear equipos |
| GET / PUT / PATCH / DELETE | `/devices/{device_id}` | CRUD del dispositivo |
| GET | `/devices/{device_id}/loans` | Historial del equipo |
| GET / POST | `/loans` | Listar / crear préstamos |
| GET | `/loans/details` | Consulta con joins, antes de la ruta dinámica |
| GET | `/loans/{loan_id}` | Detalle con usuario y dispositivo |
| PATCH | `/loans/{loan_id}/return` | Devolución sin body |

`DELETE /users/{id}` mantiene la cabecera `X-API-Key` de la actividad anterior. Las eliminaciones exitosas ahora devuelven **204 sin body**, conforme a la guía. Un usuario o dispositivo con historial no se puede eliminar, incluso después de la devolución (409).

### Ejemplo del flujo

`POST /users`:

```json
{"name":"Ana Perez","email":"ana@example.com","role":"user","is_active":true}
```

`POST /devices`:

```json
{"name":"Lenovo ThinkPad","serial_number":"LEN-001","device_type":"laptop","brand":"lenovo"}
```

`POST /loans` con los identificadores obtenidos:

```json
{"user_id":1,"device_id":1}
```

La creación valida las referencias y reserva el dispositivo mediante un `UPDATE` condicional. La reserva y el préstamo se confirman juntos; ante un fallo, se ejecuta rollback. Reintentar con el mismo equipo devuelve 409.

`PATCH /loans/1/return` registra `returned`, asigna `return_date` y habilita el dispositivo en una sola transacción. Una segunda devolución devuelve 409. El estado `overdue` se reconoce en constraints, respuestas y consultas, pero no se calcula automáticamente: la guía no define fecha de vencimiento ni política de mora.

### PUT y PATCH de dispositivos

PUT reemplaza nombre, serie, tipo, marca y disponibilidad: exige los campos no opcionales; omitir marca la deja en `null`. PATCH modifica solo los campos presentes; admite `brand: null`, rechaza otros nulos (422) y body vacío (400). Se bloquean modificaciones de dispositivos con préstamos abiertos (409) para proteger la disponibilidad.

### Filtros y joins

```text
GET /devices?device_type=laptop&is_available=true&brand=lenovo
GET /devices?search=thinkpad
GET /loans?status=active&device_type=laptop
GET /loans?user_email=ana@example.com
GET /loans?user_id=1&device_id=1
GET /loans?search=ana
GET /loans?date_from=2026-01-01T00:00:00Z&date_to=2026-12-31T23:59:59Z
```

Los filtros se combinan con AND; la búsqueda parcial usa OR entre nombre/correo del usuario y nombre del equipo. Se utilizan `join()`, `where()`, `and_()`, `or_()` e `icontains()` (LIKE sin distinguir mayúsculas y con escape de comodines). `contains_eager()` aprovecha los joins para cargar las relaciones del listado. Los tipos y marcas se comparan de forma exacta; `search` es parcial. Las fechas son inclusivas y un rango invertido devuelve 422.

`/loans` y `/loans/details` retornan una lista de `LoanDetailResponse` con campos del préstamo y objetos `user` y `device`. `/devices` devuelve una lista; `/users` conserva `{total, items}`.

## 6. Errores

| Situación | HTTP |
|---|---|
| Creación | 201 |
| Consulta, actualización o devolución | 200 |
| Eliminación | 204 |
| Email o serie duplicados; PATCH vacío | 400 |
| DELETE de usuario sin clave válida | 401 |
| Usuario, dispositivo o préstamo inexistente | 404 |
| Equipo no disponible; devolución repetida; historial protegido | 409 |
| Body o filtros inválidos | 422 |
| Fallo de base de datos | 500, mensaje sin SQL ni detalles internos |

Alembic informa errores en la terminal y devuelve código de salida distinto de cero; las migraciones no se exponen como endpoint HTTP.

## 7. Pruebas

```powershell
python -m pip install -r requirements-dev.txt
python -m pytest -q --junitxml=evidencias/pytest.xml
```

Cada prueba funcional utiliza una base temporal creada mediante `alembic upgrade head`, sin `create_all`. La suite cubre:

- Los 12 escenarios funcionales mínimos de la guía, desde la migración hasta el historial posterior a la devolución.
- CRUD y filtros de dispositivos, CRUD de usuarios, autenticación de eliminación y Swagger/OpenAPI.
- Recursos inexistentes, duplicados, datos y filtros inválidos, préstamos no disponibles y devoluciones repetidas.
- Restricciones SQL de referencias, estados, fechas y unicidad de préstamos abiertos.
- Conservación del historial, adopción de una base anterior y reversión de migraciones.
- Rollback al fallar la creación o devolución; solicitudes concurrentes de préstamo y devolución.

Resultado histórico de la Guía 10: **43 pruebas aprobadas**, sin fallos. El [resumen anterior](evidencias/RESUMEN.md) y su [reporte JUnit](evidencias/pytest.xml) se conservan. Para la última actividad, ejecutar `python -m pytest -q --junitxml=evidencias/seguridad/pytest.xml`; incluye regresión y nuevas pruebas de seguridad. El entorno de validación usa Python 3.14 en Windows.

## 8. Evidencias reproducibles

[Registro Alembic](evidencias/alembic.txt), [estructura SQL](evidencias/tables.sql), [peticiones y respuestas completas](evidencias/api.json) y [OpenAPI](evidencias/openapi.json).

Las capturas de consola y API muestran salidas reales renderizadas para su lectura; Swagger se capturó directamente en un navegador. Para regenerarlas en una base temporal:

```powershell
python scripts/generate_evidence.py
# Opcional: capturas con Microsoft Edge instalado
python -m pip install playwright
python scripts/generate_evidence.py --screenshots
```

El script reproduce `init` y `revision --autogenerate` en un directorio temporal y ejecuta `upgrade`, `history` y `check` con las revisiones del repositorio. No modifica las migraciones entregadas ni la base de la aplicación.

### Alembic y estructura

![Inicialización real de Alembic](evidencias/01-init.png)
![Generación automática de migración](evidencias/02-autogenerate.png)
![Aplicación, historial y verificación](evidencias/03-upgrade-history.png)
![Tablas, índices y restricciones](evidencias/04-tables.png)

### Swagger

![Swagger UI con Users, Devices y Loans](evidencias/swagger.png)

### Flujo y errores

![Creación de usuario](evidencias/api-01.png)
![Creación de dispositivo](evidencias/api-02.png)
![Creación de préstamo](evidencias/api-03.png)
![Dispositivo no disponible](evidencias/api-04.png)
![Consulta con joins](evidencias/api-05.png)
![Filtros combinados](evidencias/api-06.png)
![Préstamos del usuario](evidencias/api-07.png)
![Devolución](evidencias/api-08.png)
![Disponibilidad recuperada](evidencias/api-09.png)
![Historial del dispositivo](evidencias/api-10.png)
![Devolución repetida](evidencias/api-11.png)
![Filtro inválido](evidencias/api-12.png)

## 9. Git y socialización

La rama de trabajo solicitada es `device_systems_alembic_relaciones`, para integrar en `main`. No se incluyen bases locales, credenciales ni capturas antiguas eliminadas previamente por el usuario en los cambios de esta actividad.

Para socializar: mostrar `alembic history`, explicar las relaciones, crear un usuario y un dispositivo en Swagger, prestar el equipo, demostrar el 409 al repetir, consultar joins/filtros, devolver y comprobar disponibilidad e historial. Finalmente, mostrar las pruebas y explicar por qué un rollback evita datos inconsistentes.

## 10. Reflexión

Las migraciones convierten el esquema en una secuencia reproducible y revisable. Separar la base de usuarios de la ampliación permite conservar datos anteriores y conocer qué versión está instalada, algo que `create_all()` no resuelve al evolucionar tablas.

El préstamo como entidad conserva quién utilizó cada equipo y cuándo lo devolvió. Las relaciones facilitan navegar por esos datos, mientras las claves foráneas y restricciones protegen la integridad aunque se omita la API. Las transacciones mantienen sincronizados préstamo y disponibilidad.

Los joins permiten responder preguntas que una tabla aislada no puede resolver: qué equipos tiene un usuario, qué préstamos corresponden a cierto tipo de equipo y cuál es su historial. Los filtros combinables, la documentación y las pruebas convierten esas consultas en un comportamiento verificable.
