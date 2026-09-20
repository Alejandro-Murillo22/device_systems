# Resumen de la implementación y validación

Fecha de ejecución: 19 de septiembre de 2026.

## Parte 1: revisión y persistencia

- Se revisaron las 15 páginas de la Guía 10 y el proyecto existente.
- Se instaló un entorno virtual local con las dependencias de aplicación y pruebas.
- Se reemplazó la creación automática de tablas al arrancar por migraciones Alembic.
- Se crearon dos revisiones: usuarios anteriores y ampliación con dispositivos/préstamos.
- Se añadieron los modelos Device y Loan, las relaciones bidireccionales y las claves foráneas.
- Se activó la integridad referencial de SQLite y se añadió un índice único para préstamos abiertos.
- `upgrade head`, `history`, `current` y `check` se ejecutaron correctamente.

## Parte 2: funcionalidad

- CRUD de dispositivos con serie única y filtros por tipo, marca, disponibilidad y búsqueda.
- Creación de préstamos y devolución con actualización atómica de disponibilidad.
- Historial por usuario y dispositivo, consulta de equipos asignados y detalle con joins.
- Filtros de préstamos por usuario, equipo, estado, email, tipo, búsqueda y rango de fechas.
- Protección del historial frente a eliminaciones y de equipos prestados frente a modificaciones.
- Conservación del CRUD de usuarios; DELETE actualizado a 204 según la guía.
- Documentación OpenAPI organizada por Users, Devices y Loans.

## Parte 3: pruebas de funcionamiento y errores

**Resultado final: 43 passed, 2 warnings, en 55.56 segundos.**

Comando ejecutado:

```powershell
.\.venv\Scripts\python -m pytest -q --junitxml=evidencias/pytest.xml
```

| Área | Verificación |
|---|---|
| Flujo de préstamo | Crear usuario/equipo/préstamo, consultar joins, filtrar, devolver, verificar disponibilidad e historial |
| Validación | Identificadores y cuerpos inválidos, campos vacíos, nulos no permitidos, fechas y filtros inválidos |
| Recursos inexistentes | Usuarios, dispositivos y préstamos: 404 |
| Conflictos | Equipo ocupado, devolución repetida, historial protegido y equipo prestado: 409 |
| Duplicados | Email y serie; actualización fallida conserva los datos anteriores |
| Autenticación anterior | DELETE users sin clave o con clave incorrecta: 401 |
| Integridad SQL | FK, índice único parcial, estados y coherencia de fechas |
| Transacciones | Fallo de commit al prestar o devolver revierte ambos cambios |
| Concurrencia | Dos préstamos: 201/409; dos devoluciones: 200/409 |
| Migraciones | Upgrade/downgrade/upgrade, metadata, usuarios anteriores y base sin versionar |
| Errores de migración | Revisión inexistente y ruta inválida producen salida distinta de cero |
| Documentación | Swagger, ReDoc, OpenAPI y tags |
| Error interno | Respuesta 500 sin SQL ni datos técnicos de la excepción |

Las dos advertencias proceden de dependencias: transición de Starlette de httpx a httpx2 y deprecación de un alias de AnyIO. No hay fallos de pruebas.

## Parte 4: documentación y evidencias

- Se reemplazó el README anterior, que contenía secciones duplicadas y documentación desactualizada.
- Se documentaron instalación, migraciones, adopción de una base anterior, endpoints, ejemplos, errores y reflexión.
- Se generaron 17 capturas: Swagger, cuatro de Alembic/esquema y doce de peticiones/respuestas.
- Se guardaron los registros Alembic, esquema SQL, OpenAPI, respuestas JSON y reporte JUnit.
- El generador usa una base temporal; se corrigió el cierre explícito de SQLite para liberar el archivo al finalizar en Windows.
- Se utilizó la rama `device_systems_alembic_relaciones` para la integración local con `main`.

Los archivos de `pruebas/` que ya estaban eliminados al comenzar no forman parte del commit de esta actividad. No se publicaron cambios en GitHub desde esta ejecución. La socialización indicada en la guía se deja preparada con un guion en el README para que el aprendiz la realice.
