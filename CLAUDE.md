# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Estado actual

El repositorio contiene **solo la especificación**: `emergency-platform-spec.md`. No hay código todavía. Ese documento es la **fuente de verdad** del proyecto y debe leerse antes de escribir nada; este archivo resume lo que se pierde si solo se leen archivos sueltos.

La construcción va por fases (§10 del spec) y **hay que detenerse al final de cada fase para que el usuario verifique**:

1. ~~Base (compose, Postgres+PostGIS, migraciones, seeds, Makefile)~~ — hecha
2. ~~Intake (triage + tests)~~ — hecha; sirve de plantilla para los otros tres servicios

3. Dispatch (nearby PostGIS, asignación con bloqueo, auto-asignación)
4. Geospatial + Notification (hotspots, SSE)
5. Gateway + Frontend
6. Supabase (RLS, Realtime)

Ante ambigüedad en el spec: **preguntar, no inventar**. No cambiar rutas, nombres de campos, enums ni el formato de respuesta.

## Comandos (a crear en Fase 1; Makefile en la raíz)

```bash
make up       # docker compose up --build  — único comando necesario para levantar todo
make down
make logs
make seed     # carga database/seeds/*
make test
make reset    # borra el volumen de Postgres y recrea
```

Convención esperada para tests: `pytest` por servicio (`cd services/intake && pytest`), un test único con `pytest tests/test_triage.py::test_name`. El e2e vive en `tests/e2e/test_flow.py` y golpea el gateway con `httpx`.

## Plantilla de servicio

`services/intake/` es la referencia estructural para Dispatch, Geospatial y
Notification: `config.py` (pydantic-settings), `log.py` (JSON + `request_id` en un
ContextVar), `errors.py` (`ApiError` + tabla código→estado), `responses.py`
(`success`/`failure`), los cuatro exception handlers de `main.py` y el Dockerfile
con targets `local`/`lambda`. Se **duplica** en cada servicio, no se extrae a un
paquete común: el spec prohíbe compartir un paquete de dominio.

Dos trampas ya encontradas ahí: los modelos de respuesta llevan `extra="forbid"`,
así que hay que construirlos campo a campo desde la fila y no con `Model(**row)`;
y `failure()` deriva el estado HTTP del código, de modo que un 4xx sin equivalente
(405, 415) debe mapearse a `INVALID_PAYLOAD` y nunca a `INTERNAL_ERROR`.

## Arquitectura

Cuatro microservicios **independientes** (nada de backend monolítico), detrás de un gateway Nginx, con un frontend React:

```
frontend :3000 → gateway :8080 → intake :8001 | dispatch :8002 | geospatial :8003 | notification :8004
                                              → PostgreSQL 16 + PostGIS :5432
```

- El frontend **solo** habla con `http://localhost:8080` (`VITE_API_BASE_URL`), nunca con los puertos de los servicios. Así migrar a API Gateway es cambiar una variable.
- Cada servicio repite la misma estructura interna: `app/{main,config,db}.py` + `routes/ schemas/ services/ repositories/ clients/`. **No se comparte un paquete de dominio común entre servicios**; duplicar utilidades pequeñas es aceptable y deliberado.
- Un **esquema Postgres por servicio** (`intake`, `dispatch`, `geo`, `notification`). Ningún servicio escribe en el esquema de otro. Única excepción documentada: `geospatial` tiene `SELECT` de solo lectura sobre `intake.emergencies` vía el rol `geo_reader`.
- `dispatch.assignments.emergency_id` va **sin FK** a propósito: cruza esquema y servicio.

### Orquestación (acoplamiento entre servicios)

`POST /v1/emergencies` en Intake dispara dos llamadas **fire-and-forget** (`httpx.AsyncClient`, timeout 3 s, fallo silencioso registrado en log): la notificación `EMERGENCY_CREATED` y `POST /v1/internal/dispatches/auto` en Dispatch. Si Notification o Dispatch están caídos, la emergencia **igual se crea y se responde 201**. Toda llamada saliente vive en `app/clients/`.

Dispatch, al asignar: bloquea el recurso con `SELECT ... FOR UPDATE` (doble asignación → `RESOURCE_UNAVAILABLE`), llama a Intake para pasar la emergencia a `ASSIGNED` y crea la notificación `RESOURCE_ASSIGNED`. Sin recurso disponible responde `200` con `{"assigned": false, "reason": "NO_RESOURCE_AVAILABLE"}` — nunca un error.

### Invariantes que se rompen fácil

- **Formato de respuesta uniforme**: `{"success": true, "data": {}}` / `{"success": false, "error": {"code", "message"}}`. Requiere un `exception_handler` global en cada servicio para que **también** los errores de validación de FastAPI salgan así.
- **camelCase en la API, snake_case en la BD** — alias generator en los modelos Pydantic.
- `details` es un `Union` discriminado por `type`; un `details` que no corresponda al tipo → `INVALID_PAYLOAD`. Lat/lon deben caer en el bounding box de Colombia (lat −4.5..13, lon −82..−66).
- `location GEOGRAPHY(POINT,4326)` se deriva **siempre** de `latitude`/`longitude` mediante trigger `BEFORE INSERT OR UPDATE`, nunca desde la aplicación.
- Máquina de estados: `RECEIVED → TRIAGED → ASSIGNED → IN_PROGRESS → RESOLVED`, con `CANCELLED` desde cualquier estado no final. Cualquier otra transición → `CONFLICT`.
- Triage: función **pura** `calculate_priority(type, details) -> Priority` en `services/intake/app/services/triage.py`, con tests que cubran todos los casos (reglas en §4). Campos opcionales ausentes = `0`/`false`.
- Migraciones numeradas en `database/migrations/` y **idempotentes** (`IF NOT EXISTS`, `DO $$...$$`) porque el mismo SQL se ejecuta después en Supabase sin cambios.

### Preparación para AWS (dejar listo, no desplegar)

`handler = Mangum(app)` al final de cada `main.py`; Dockerfile multi-stage con targets `local` (uvicorn) y `lambda` (`public.ecr.aws/lambda/python:3.12`); sin estado en memoria entre requests ni tareas de fondo que sobrevivan a la respuesta; toda config por env vars en `config.py`; logs JSON a stdout con `request_id`/`service`/`level`; `/health` por servicio que verifique la BD; `infrastructure/` vacío con `.gitkeep`.

**No implementar todavía**: Lambda, API Gateway, ECR, CodeDeploy, Canary, CI/CD, Secrets Manager, Budgets.

### Local ↔ Supabase

Una sola variable, `DATABASE_URL`. El código no distingue entre entornos. Los microservicios usan el service role (bypass de RLS) porque autorizan a nivel de aplicación; el frontend usa la anon key y **sí** queda sujeto a RLS. En el cliente JS hay que indicar el esquema explícitamente (`.schema('intake')`) porque las tablas no están en `public`.

## Stack

Backend: Python 3.12, FastAPI, Pydantic v2, Mangum, SQLAlchemy 2.x async + asyncpg, GeoAlchemy2, httpx, pytest + pytest-asyncio. **Nada de ORM sync ni `psycopg2` bloqueante.**
Frontend: React + TypeScript + Vite, React Router, TanStack Query, Supabase JS, Leaflet + OpenStreetMap, Tailwind.

## Convenciones

- Código, nombres de tablas y columnas, y commits en **inglés**; documentación (`README.md`, `docs/`) en **español**.
- Conventional Commits con scope de servicio: `feat(intake): ...`.
