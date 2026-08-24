# device_systems

API REST desarrollada con **FastAPI** para la gestión del recurso **users** dentro del sistema `device_systems`. Este proyecto corresponde a la actividad *"Fundamentos de FastAPI: API REST para Gestión de Usuarios"* (Clase 7), e integra: instalación y configuración de FastAPI, métodos HTTP GET y POST, Path Parameters, Query Parameters, validación de datos con Pydantic v2, cabeceras HTTP personalizadas y Response Models.

## 1. Descripción de la aplicación

`device_systems` es una API REST que permite administrar los usuarios de un sistema. Sobre el recurso `users` es posible:

- Listar todos los usuarios, con filtros opcionales por **rol** y por **estado activo/inactivo**.
- Consultar un usuario específico por su **ID**.
- Registrar un nuevo usuario, validando los datos de entrada y evitando **correos duplicados**.

La API valida automáticamente los datos usando **Pydantic v2** (tipos, formato de correo, longitud mínima del nombre, valores permitidos de rol, etc.), estandariza las respuestas mediante **response models** (ocultando campos internos como `internal_notes`) y agrega **cabeceras HTTP personalizadas** (`X-App-Name`, `X-API-Version`) a todas las respuestas.

### Estructura del proyecto

```
device_systems/
│── app/
│   │── main.py                 # Punto de entrada, middleware de cabeceras
│   │── schemas/
│   │   └── user_schema.py      # Modelos Pydantic (UserCreate, UserPublic, UserInDB...)
│   │── routes/
│   │   └── user_routes.py      # Endpoints GET y POST del recurso users
│── requirements.txt
│── README.md
```

## 2. Instalación de dependencias

**Requisitos previos:** Python 3.10+ instalado, y opcionalmente Git.

1. Clonar o descomprimir el proyecto y ubicarse en la carpeta raíz:

   ```bash
   cd device_systems
   ```

2. Crear un entorno virtual (recomendado):

   ```bash
   python -m venv venv
   ```

3. Activar el entorno virtual:

   - **Windows (PowerShell):**
     ```bash
     venv\Scripts\Activate.ps1
     ```
   - **Linux / macOS:**
     ```bash
     source venv/bin/activate
     ```

4. Instalar las dependencias:

   ```bash
   pip install -r requirements.txt
   ```

   Dependencias principales:
   - `fastapi`
   - `uvicorn[standard]`
   - `pydantic` (v2)
   - `email-validator` (requerido por Pydantic para validar `EmailStr`)

## 3. Ejecución del servidor

Desde la carpeta raíz del proyecto (`device_systems/`):

```bash
uvicorn app.main:app --reload
```

- La API quedará disponible en: `http://127.0.0.1:8000`
- Documentación interactiva (Swagger UI): `http://127.0.0.1:8000/docs`
- Documentación alternativa (ReDoc): `http://127.0.0.1:8000/redoc`

> El proyecto incluye 3 usuarios de ejemplo precargados en memoria (`id` 1, 2 y 3) para poder probar los endpoints GET inmediatamente después de levantar el servidor.

## 4. Tabla de endpoints

| Método | Endpoint                     | Descripción                                              | Body / Parámetros                                  |
|--------|-------------------------------|-----------------------------------------------------------|-----------------------------------------------------|
| GET    | `/`                            | Verifica el estado de la API                              | —                                                     |
| GET    | `/users`                       | Lista todos los usuarios                                  | Query opcionales: `role`, `is_active`               |
| GET    | `/users?role=admin`            | Filtra usuarios por rol                                    | Query: `role` (`admin`, `support`, `user`)          |
| GET    | `/users?is_active=true`        | Filtra usuarios por estado activo/inactivo                 | Query: `is_active` (`true` / `false`)               |
| GET    | `/users/{user_id}`             | Consulta un usuario por su ID (Path Parameter)             | Path: `user_id` (int)                                |
| POST   | `/users`                       | Registra un nuevo usuario                                  | Body JSON: `name`, `email`, `role`, `is_active`     |

**Cabeceras personalizadas** (presentes en todas las respuestas de `/users*`):

```
X-App-Name: device_systems
X-API-Version: 1.0
```

**Códigos de estado relevantes:**

| Código | Cuándo ocurre                                              |
|--------|-------------------------------------------------------------|
| 200    | Consulta exitosa (GET)                                      |
| 201    | Usuario creado exitosamente (POST)                           |
| 404    | Usuario no encontrado (`GET /users/{id}`)                    |
| 409    | Correo ya registrado (`POST /users`)                          |
| 422    | Error de validación de datos (Pydantic)                       |

## 5. Ejemplos de peticiones

### GET /users

**Request:**
```
GET http://127.0.0.1:8000/users
```

**Response (200):**
```json
{
  "total": 3,
  "items": [
    {
      "id": 1,
      "name": "Alejandro Ramirez",
      "email": "alejandro@device-systems.com",
      "role": "admin",
      "is_active": true
    },
    {
      "id": 2,
      "name": "Juan Duque",
      "email": "juan@device-systems.com",
      "role": "support",
      "is_active": true
    },
    {
      "id": 3,
      "name": "Mateo Gomez",
      "email": "mateo@device-systems.com",
      "role": "user",
      "is_active": false
    }
  ]
}
```

### GET /users/{user_id}

**Request:**
```
GET http://127.0.0.1:8000/users/1
```

**Response (200):**
```json
{
  "id": 1,
  "name": "Alejandro Ramirez",
  "email": "alejandro@device-systems.com",
  "role": "admin",
  "is_active": true
}
```

**Response si el usuario no existe (404):**
```json
{
  "detail": "Usuario con id 99 no encontrado"
}
```

### GET /users?role=admin&is_active=true

**Request:**
```
GET http://127.0.0.1:8000/users?role=admin&is_active=true
```

**Response (200):** devuelve solo los usuarios que cumplen ambos filtros.

### POST /users

**Request:**
```
POST http://127.0.0.1:8000/users
Content-Type: application/json

{
  "name": "Camila Torres",
  "email": "camila@device-systems.com",
  "role": "user",
  "is_active": true
}
```

**Response (201):**
```json
{
  "id": 4,
  "name": "Camila Torres",
  "email": "camila@device-systems.com",
  "role": "user",
  "is_active": true
}
```

**Response si el correo ya existe (409):**
```json
{
  "detail": "El correo 'camila@device-systems.com' ya está registrado"
}
```

**Response si los datos no son válidos (422)**, por ejemplo `name` con menos de 3 caracteres o `role` con un valor no permitido:
```json
{
  "detail": [
    {
      "type": "string_too_short",
      "loc": ["body", "name"],
      "msg": "String should have at least 3 characters"
    }
  ]
}
```

## 6. Evidencias de pruebas (capturas)



### 6.1 Swagger UI

![Swagger UI](pruebas/Swaggerui.png)

### 6.2 Evidencia GET /users

![GET /users - 200 OK](pruebas/getUsers.png)

### 6.3 Evidencia GET /users/{user_id}

![GET /users/{user_id} - 200 OK](pruebas/getUserId.png)

### 6.4 Evidencia POST /users

![POST /users - 201 Created](pruebas/postUsers.png)

### 6.5 Evidencia de validaciones y errores
![GET /999 - 404 Not Found](pruebas/getUserIdError.png)
![JSON NAME Incorrecto - 422 Unprocessable Content](pruebas/postUsersNameError.png)
![JSON EMAIL Incorrecto - 422 Unprocessable Content](pruebas/postUsersEmailError.png)
![JSON EMAIL Duplicado - 409 Conflict](pruebas/postUsersEmailDuplicate.png)

## 7. Reflexión sobre el uso de FastAPI para construir APIs REST

FastAPI permite construir APIs REST de forma rápida y con un alto nivel de confiabilidad gracias a su integración nativa con Pydantic: los datos de entrada se validan automáticamente antes de que lleguen a la lógica de negocio, lo que reduce errores y código repetitivo de validación manual. El uso de *response models* separa claramente lo que el cliente puede enviar (`UserCreate`) de lo que puede recibir (`UserPublic`), permitiendo ocultar campos internos sin duplicar lógica. Además, la documentación interactiva (Swagger UI) se genera automáticamente a partir del código y los esquemas, lo que facilita enormemente las pruebas funcionales y la comunicación con otros desarrolladores o consumidores de la API. En conjunto, estas características hacen de FastAPI una herramienta muy adecuada para proyectos como `device_systems`, donde la gestión correcta de usuarios depende directamente de validaciones estrictas y respuestas consistentes.

## 8. Autor

Proyecto desarrollado por Alejandro Murillo — Programa ADSO, Ficha 3223877, SENA CTMA.
