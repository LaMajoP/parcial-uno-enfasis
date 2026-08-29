# Emergency Platform — Especificación de construcción (Fase Local + Supabase)

> **Alcance histórico:** este documento describe las fases locales iniciales. La
> fase de producción AWS posterior está implementada y documentada en
> [`docs/despliegue-produccion.md`](docs/despliegue-produccion.md); esa guía tiene
> prioridad para Lambda, API Gateway, secretos, AppConfig, CI/CD y Budgets.
> Sí debes dejar el código *preparado* para AWS: cada servicio expone `handler = Mangum(app)` y su Dockerfile tiene un target `lambda`.
> Si algo de este documento es ambiguo, **pregunta antes de inventar**. No cambies los contratos de API ni los nombres de enums.

---

## 0. Objetivo

Plataforma de gestión de emergencias con dos perfiles de usuario:

- **Ciudadano:** reporta una emergencia (tipo, ciudad, ubicación, personas afectadas, detalles).
- **Operador:** ve el dashboard de emergencias activas (prioridad, ubicación, estado, recurso asignado, mapa).

Arquitectura de **4 microservicios independientes** + gateway + frontend. Nada de un backend monolítico.

```
                 FRONTEND (React, :3000)
                          |
                 GATEWAY LOCAL (:8080)
                          |
      +-------------+-----+-------+-------------+
      |             |             |             |
   Intake        Dispatch     Geospatial   Notification
    :8001         :8002         :8003         :8004
      |             |             |             |
      +-------------+-------------+-------------+
                          |
              PostgreSQL + PostGIS (:5432)
```

**Responsabilidades:**

| Servicio | Responsabilidad |
|---|---|
| **Intake & Triage** | Recibe la emergencia, valida, calcula prioridad (P1–P4), persiste, dispara notificación y auto-despacho |
| **Dispatch & Resource Assignment** | Busca recursos disponibles y cercanos, asigna, actualiza estado del despacho |
| **Geospatial & Zone Aggregation** | Consultas por zona y cálculo de hotspots (concentración de emergencias) con PostGIS |
| **Notification & Status Broadcast** | Registra y difunde los cambios de estado (Realtime en fase Supabase) |

---

## 1. Stack obligatorio

**Backend:** Python 3.12, FastAPI, Pydantic v2, Mangum, SQLAlchemy 2.x (async) + asyncpg, GeoAlchemy2, `httpx` para comunicación entre servicios, `pytest` + `pytest-asyncio`.

**Frontend:** React + TypeScript + Vite, React Router, TanStack Query, Supabase JS, Leaflet + OpenStreetMap, Tailwind.

**Datos:** PostgreSQL 16 + PostGIS (imagen `postgis/postgis:16-3.4` en local; Supabase en la nube después).

**Infra local:** Docker + Docker Compose.

**Regla:** todo el proyecto debe levantarse con **`docker compose up --build`** y nada más. Cualquiera clona el repo y funciona sin archivos `.env`.

---

## 2. Estructura del repositorio (monorepo)

Créala exactamente así:

```
emergency-platform/
├── services/
│   ├── intake/
│   │   ├── app/
│   │   │   ├── main.py            # FastAPI app + handler = Mangum(app)
│   │   │   ├── config.py          # Settings con pydantic-settings
│   │   │   ├── db.py              # engine/session async
│   │   │   ├── routes/
│   │   │   ├── schemas/           # Pydantic request/response
│   │   │   ├── services/          # lógica de negocio (triage.py aquí)
│   │   │   ├── repositories/      # acceso a datos (SQL/SQLAlchemy)
│   │   │   └── clients/           # llamadas HTTP a otros servicios
│   │   ├── tests/
│   │   ├── Dockerfile
│   │   └── requirements.txt
│   ├── dispatch/          # misma estructura
│   ├── geospatial/        # misma estructura
│   └── notification/      # misma estructura
├── gateway/
│   ├── nginx.conf                 # gateway local (reverse proxy)
│   └── Dockerfile
├── frontend/
│   ├── src/
│   ├── package.json
│   └── vite.config.ts
├── database/
│   ├── migrations/                # SQL numerado, idempotente
│   ├── rls/                       # políticas RLS (se aplican en Supabase)
│   └── seeds/                     # recursos y datos de prueba
├── infrastructure/                # VACÍO por ahora (fase AWS)
├── docs/
│   └── diagrams/
├── docker-compose.yml
├── Makefile
└── README.md
```

**Convenciones:** código, nombres de tablas/columnas y commits en inglés; documentación (`README`, `docs/`) en español. Commits estilo Conventional Commits (`feat(intake): ...`).

---

## 3. Modelo de datos

Un **esquema por microservicio** para mantener autonomía. Ningún servicio escribe en el esquema de otro.

```
auth          └── users              (Supabase Auth; en local se simula)
intake        └── emergencies
dispatch      ├── resources
              └── assignments
geo           └── hotspots
notification  └── notifications
```

**Excepción documentada:** el servicio `geospatial` necesita leer `intake.emergencies` para agregar por zona. Se le concede `SELECT` de solo lectura sobre esa tabla mediante un rol dedicado (`geo_reader`). Es la única lectura cruzada permitida; queda registrada en `docs/decisiones.md` como trade-off consciente frente a duplicar datos.

### 3.1 Enums

```sql
CREATE TYPE emergency_type   AS ENUM ('RESCUE','SHELTER','SUPPLIES','STRUCTURAL_DAMAGE');
CREATE TYPE priority_type    AS ENUM ('P1','P2','P3','P4');
CREATE TYPE city_type        AS ENUM ('CHOCO','PEREIRA','CALI','MANIZALES');
CREATE TYPE emergency_status AS ENUM ('RECEIVED','TRIAGED','ASSIGNED','IN_PROGRESS','RESOLVED','CANCELLED');
CREATE TYPE resource_type    AS ENUM ('AMBULANCE','FIRE_BRIGADE','RESCUE_TEAM','CIVIL_DEFENSE','HUMANITARIAN_TEAM');
CREATE TYPE resource_status  AS ENUM ('AVAILABLE','ASSIGNED','UNAVAILABLE');
CREATE TYPE assignment_status AS ENUM ('ASSIGNED','ACCEPTED','IN_PROGRESS','COMPLETED','CANCELLED');
CREATE TYPE notification_channel AS ENUM ('REALTIME','WEBHOOK');
CREATE TYPE notification_status  AS ENUM ('PENDING','SENT','FAILED');
CREATE TYPE notification_event   AS ENUM ('EMERGENCY_CREATED','STATUS_CHANGED','RESOURCE_ASSIGNED','HOTSPOT_DETECTED');
```

### 3.2 Tablas

```sql
-- intake.emergencies
id           UUID PRIMARY KEY DEFAULT gen_random_uuid()
type         emergency_type      NOT NULL
priority     priority_type       NOT NULL
city         city_type           NOT NULL
status       emergency_status    NOT NULL DEFAULT 'RECEIVED'
latitude     DOUBLE PRECISION    NOT NULL
longitude    DOUBLE PRECISION    NOT NULL
location     GEOGRAPHY(POINT,4326) NOT NULL
details      JSONB               NOT NULL DEFAULT '{}'
citizen_id   UUID                NULL
created_at   TIMESTAMPTZ         NOT NULL DEFAULT now()
updated_at   TIMESTAMPTZ         NOT NULL DEFAULT now()

-- dispatch.resources
id           UUID PRIMARY KEY DEFAULT gen_random_uuid()
name         VARCHAR(120)        NOT NULL
type         resource_type       NOT NULL
city         city_type           NOT NULL
status       resource_status     NOT NULL DEFAULT 'AVAILABLE'
latitude     DOUBLE PRECISION    NOT NULL
longitude    DOUBLE PRECISION    NOT NULL
location     GEOGRAPHY(POINT,4326) NOT NULL
created_at   TIMESTAMPTZ         NOT NULL DEFAULT now()
updated_at   TIMESTAMPTZ         NOT NULL DEFAULT now()

-- dispatch.assignments
id            UUID PRIMARY KEY DEFAULT gen_random_uuid()
emergency_id  UUID              NOT NULL          -- sin FK: cruza esquema/servicio
resource_id   UUID              NOT NULL REFERENCES dispatch.resources(id)
status        assignment_status NOT NULL DEFAULT 'ASSIGNED'
assigned_at   TIMESTAMPTZ       NOT NULL DEFAULT now()
completed_at  TIMESTAMPTZ       NULL

-- geo.hotspots
id               UUID PRIMARY KEY DEFAULT gen_random_uuid()
city             city_type NOT NULL
center           GEOGRAPHY(POINT,4326) NOT NULL
radius_meters    INTEGER   NOT NULL
emergency_count  INTEGER   NOT NULL
highest_priority priority_type NOT NULL
generated_at     TIMESTAMPTZ NOT NULL DEFAULT now()

-- notification.notifications
id            UUID PRIMARY KEY DEFAULT gen_random_uuid()
emergency_id  UUID NOT NULL
recipient_id  UUID NULL
channel       notification_channel NOT NULL
event_type    notification_event   NOT NULL
payload       JSONB NOT NULL DEFAULT '{}'
status        notification_status  NOT NULL DEFAULT 'PENDING'
created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
sent_at       TIMESTAMPTZ NULL
```

**Índices obligatorios:**

```sql
CREATE INDEX ON intake.emergencies USING GIST (location);
CREATE INDEX ON intake.emergencies (city, status, priority);
CREATE INDEX ON intake.emergencies (created_at DESC);
CREATE INDEX ON dispatch.resources USING GIST (location);
CREATE INDEX ON dispatch.resources (city, type, status);
CREATE INDEX ON dispatch.assignments (emergency_id);
CREATE INDEX ON notification.notifications (emergency_id, created_at DESC);
```

**Reglas adicionales:**
- `location` se calcula siempre desde `latitude`/`longitude` con `ST_SetSRID(ST_MakePoint(lon, lat), 4326)::geography`. Usa un trigger `BEFORE INSERT OR UPDATE` para que nunca queden desincronizados.
- Trigger `set_updated_at()` en `emergencies` y `resources`.
- Las migraciones van en `database/migrations/`, numeradas (`001_extensions.sql`, `002_schemas.sql`, `003_enums.sql`, `004_tables.sql`, `005_indexes.sql`, `006_triggers.sql`, `007_grants.sql`) y deben ser **idempotentes** (`IF NOT EXISTS`, `DO $$ ... $$`), porque el mismo SQL se ejecutará luego en Supabase.

### 3.3 Seeds

`database/seeds/001_resources.sql` con **mínimo 4 recursos por ciudad** (Chocó, Pereira, Cali, Manizales), cubriendo los 5 tipos de recurso y con coordenadas reales dispersas dentro de cada ciudad. Nombres tipo `"Ambulancia Cali 01"`.

Coordenadas de referencia por ciudad (centro):

| Ciudad | lat | lon |
|---|---|---|
| CHOCO (Quibdó) | 5.6947 | -76.6611 |
| PEREIRA | 4.8143 | -75.6946 |
| CALI | 3.4516 | -76.5320 |
| MANIZALES | 5.0703 | -75.5138 |

Añade también `database/seeds/002_emergencies_demo.sql` con ~20 emergencias repartidas (varias concentradas en un radio pequeño de Cali) para que los **hotspots** den un resultado visible en la demo.

---

## 4. Reglas de triage (Intake)

Implementar en `services/intake/app/services/triage.py` como función pura `calculate_priority(type, details) -> Priority`, **con tests unitarios que cubran todos los casos**.

**Prioridad base por tipo:**

| Tipo | Base |
|---|---|
| `RESCUE` (búsqueda/rescate o médica) | **P1** |
| `SHELTER` (albergue) | **P2** |
| `SUPPLIES` (suministros) | **P3** |
| `STRUCTURAL_DAMAGE` (daños estructurales) | **P4** |

**Ajustes deterministas (se aplican después de la base):**

```
RESCUE:
  - Se mantiene P1 si injured > 0 OR trapped > 0 OR fire == true OR gasLeak == true
  - Baja a P2 si no hay heridos, ni atrapados, ni fuego, ni fuga de gas

SHELTER:
  - Sube a P1 si accessibilityRequired == true
                OR (children + elderly) >= 3
                OR (houseHabitable == false AND (adults + children + elderly) >= 5)
  - Si no, P2

SUPPLIES:
  - Sube a P2 si people >= 20 OR 'WATER' in categories
  - Si no, P3

STRUCTURAL_DAMAGE:
  - Sube a P2 si collapseRisk == true
  - Sube a P3 si crackLevel == 'HIGH'
  - Si no, P4
```

Si un campo opcional no viene, trátalo como `0` / `false`. La prioridad nunca puede quedar fuera de P1–P4.

Tras calcular la prioridad, el estado de la emergencia pasa de `RECEIVED` a `TRIAGED` en la misma transacción.

---

## 5. Contratos de API (NO MODIFICAR)

### Formato de respuesta

Éxito:
```json
{ "success": true, "data": {} }
```

Error:
```json
{ "success": false, "error": { "code": "INVALID_PAYLOAD", "message": "Invalid emergency payload" } }
```

Códigos de error a usar: `INVALID_PAYLOAD` (400), `UNAUTHORIZED` (401), `FORBIDDEN` (403), `NOT_FOUND` (404), `CONFLICT` (409), `RESOURCE_UNAVAILABLE` (409), `INTERNAL_ERROR` (500).
Registra un `exception_handler` global en cada servicio para que **todas** las respuestas, incluidas las de validación de FastAPI, salgan con ese formato.

Todos los payloads y respuestas usan **camelCase**; las columnas en base de datos usan **snake_case**. Configura los modelos Pydantic con un alias generator.

### 5.1 Intake Lambda

**`POST /v1/emergencies`**

Request `RESCUE`:
```json
{
  "type": "RESCUE",
  "city": "CALI",
  "location": { "latitude": 3.4516, "longitude": -76.532 },
  "details": { "injured": 2, "trapped": 1, "fire": true, "gasLeak": false }
}
```

Request `SHELTER`:
```json
{
  "type": "SHELTER",
  "city": "PEREIRA",
  "location": { "latitude": 4.8143, "longitude": -75.6946 },
  "details": { "adults": 4, "children": 2, "elderly": 1, "accessibilityRequired": false, "houseHabitable": false }
}
```

Request `SUPPLIES`:
```json
{
  "type": "SUPPLIES",
  "city": "CHOCO",
  "location": { "latitude": 5.6947, "longitude": -76.6611 },
  "details": { "categories": ["WATER", "FOOD"], "people": 15 }
}
```

Request `STRUCTURAL_DAMAGE`:
```json
{
  "type": "STRUCTURAL_DAMAGE",
  "city": "MANIZALES",
  "location": { "latitude": 5.0703, "longitude": -75.5138 },
  "details": { "buildingType": "RESIDENTIAL", "crackLevel": "HIGH", "collapseRisk": true, "photoUrl": "https://..." }
}
```

Response `201`:
```json
{
  "success": true,
  "data": {
    "id": "uuid", "type": "RESCUE", "priority": "P1",
    "city": "CALI", "status": "TRIAGED", "createdAt": "2026-08-17T17:00:00Z"
  }
}
```

**Validación:** `details` es un `Union` discriminado por `type` en Pydantic. Un `details` que no corresponda al tipo → `INVALID_PAYLOAD`. Valida también que lat/lon estén dentro de un bounding box razonable de Colombia (lat −4.5..13, lon −82..−66).

**`GET /v1/emergencies/{emergencyId}`**
```json
{
  "success": true,
  "data": {
    "id": "uuid", "type": "RESCUE", "priority": "P1", "city": "CALI",
    "status": "ASSIGNED",
    "location": { "latitude": 3.4516, "longitude": -76.532 },
    "details": {}, "createdAt": "2026-08-17T17:00:00Z"
  }
}
```

**`PATCH /v1/emergencies/{emergencyId}/status`** *(interno/operador; necesario para el flujo de estados)*
Request: `{ "status": "IN_PROGRESS" }`. Valida la transición contra la máquina de estados de §6.

### 5.2 Dispatch Lambda

**`GET /v1/resources/nearby`**
Query: `?latitude=3.4516&longitude=-76.532&radiusMeters=10000&type=AMBULANCE` (`type` opcional, `radiusMeters` por defecto 10000, `limit` por defecto 10).

```json
{
  "success": true,
  "data": [
    { "id": "uuid", "name": "Ambulancia Cali 01", "type": "AMBULANCE", "status": "AVAILABLE", "distanceMeters": 1350 }
  ]
}
```
Implementar con `ST_DWithin(location, :point, :radius)` y ordenar por `ST_Distance`. Solo devuelve recursos `AVAILABLE`.

**`POST /v1/dispatches`**
Request: `{ "emergencyId": "uuid", "resourceId": "uuid" }`

Response `201`:
```json
{
  "success": true,
  "data": {
    "id": "uuid", "emergencyId": "uuid", "resourceId": "uuid",
    "status": "ASSIGNED", "assignedAt": "2026-08-17T17:10:00Z"
  }
}
```
Efectos: marca el recurso como `ASSIGNED` (con `SELECT ... FOR UPDATE` para evitar doble asignación → `RESOURCE_UNAVAILABLE` si ya no está libre), llama a Intake para pasar la emergencia a `ASSIGNED`, y crea la notificación `RESOURCE_ASSIGNED`.

**`PATCH /v1/dispatches/{dispatchId}`**
Request: `{ "status": "IN_PROGRESS" }`. Al pasar a `COMPLETED`: setea `completed_at`, libera el recurso (`AVAILABLE`) y pone la emergencia en `RESOLVED`.

**`POST /v1/internal/dispatches/auto`** *(interno, no se expondrá en API Gateway)*
Request: `{ "emergencyId": "uuid" }`. Busca el mejor recurso disponible según el mapeo de §6 y lo asigna. Si no hay recurso, responde `200` con `{ "success": true, "data": { "assigned": false, "reason": "NO_RESOURCE_AVAILABLE" } }` — **nunca** hagas fallar el reporte de la emergencia por esto.

### 5.3 Geospatial Lambda

**`GET /v1/zones/{city}/emergencies`** — opcionales: `?priority=P1&status=RECEIVED&limit=50`

**`GET /v1/zones/{city}/hotspots`** — `?radiusMeters=5000`
```json
{
  "success": true,
  "data": [
    { "latitude": 3.452, "longitude": -76.531, "radiusMeters": 5000, "emergencyCount": 18, "highestPriority": "P1" }
  ]
}
```
Cálculo: agrupa emergencias activas (estado distinto de `RESOLVED`/`CANCELLED`) de la ciudad con `ST_ClusterDBSCAN(location::geometry, eps, minpoints)`; el centro de cada cluster es `ST_Centroid`. Persiste el resultado en `geo.hotspots` (borra los previos de esa ciudad y reinserta) y devuélvelo.

### 5.4 Notification Lambda

**`POST /v1/notifications`**
```json
{
  "emergencyId": "uuid",
  "eventType": "STATUS_CHANGED",
  "channel": "REALTIME",
  "payload": { "status": "IN_PROGRESS" }
}
```
En fase local: inserta la fila con `status = SENT` y expón además `GET /v1/notifications?emergencyId=...` y un `GET /v1/notifications/stream` (SSE) para que el dashboard se actualice sin polling. En fase Supabase, ese SSE se reemplaza por Realtime.

---

## 6. Flujo y máquina de estados

**Estados de emergencia:** `RECEIVED → TRIAGED → ASSIGNED → IN_PROGRESS → RESOLVED`, con `CANCELLED` alcanzable desde cualquier estado no final. Rechaza cualquier otra transición con `CONFLICT`.

**Orquestación (quién llama a quién):**

```
POST /v1/emergencies
  └─ Intake: valida → calcula prioridad → guarda (TRIAGED)
       ├─ POST /v1/notifications  (EMERGENCY_CREATED)   [fire-and-forget]
       └─ POST /v1/internal/dispatches/auto             [fire-and-forget]
            └─ Dispatch: busca recurso → asigna
                 ├─ PATCH /v1/emergencies/{id}/status → ASSIGNED
                 └─ POST /v1/notifications (RESOURCE_ASSIGNED)
```

Las llamadas salientes van en `app/clients/`, con `httpx.AsyncClient`, timeout de 3 s y **fallo silencioso registrado en log**: si Notification o Dispatch están caídos, la emergencia igual queda creada y el `POST /v1/emergencies` responde `201`.

**Mapeo emergencia → tipo de recurso preferido (en orden de preferencia):**

| Tipo emergencia | Recursos |
|---|---|
| `RESCUE` | `AMBULANCE`, `RESCUE_TEAM` |
| `SHELTER` | `CIVIL_DEFENSE`, `HUMANITARIAN_TEAM` |
| `SUPPLIES` | `HUMANITARIAN_TEAM`, `CIVIL_DEFENSE` |
| `STRUCTURAL_DAMAGE` | `FIRE_BRIGADE`, `RESCUE_TEAM` |

Criterio de selección: entre los `AVAILABLE` de la misma ciudad dentro del radio, el más cercano del primer tipo preferido; si no hay, el segundo tipo; si tampoco, cualquiera disponible en la ciudad.

---

## 7. Gateway local

Nginx en `:8080` como reverse proxy, enrutando por prefijo:

```
/v1/emergencies            → intake:8001
/v1/zones/                 → geospatial:8003
/v1/resources/nearby       → dispatch:8002
/v1/dispatches             → dispatch:8002
/v1/notifications          → notification:8004
/health                    → agregado de los 4 /health
```

Configura CORS permitiendo `http://localhost:3000`. Propaga un header `X-Request-Id` (genéralo si no viene) y que cada servicio lo incluya en sus logs.

**Importante:** el frontend **solo** habla con `http://localhost:8080`. Nunca con los puertos de los servicios directamente. Así el cambio a API Gateway en AWS es solo cambiar una variable de entorno.

---

## 8. Docker

Cada servicio con un `Dockerfile` **multi-stage con dos targets**:

```dockerfile
# ---- base ----
FROM python:3.12-slim AS base
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app ./app

# ---- local: uvicorn ----
FROM base AS local
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---- lambda: preparado para ECR (NO se usa todavía) ----
FROM public.ecr.aws/lambda/python:3.12 AS lambda
COPY requirements.txt ${LAMBDA_TASK_ROOT}/
RUN pip install --no-cache-dir -r ${LAMBDA_TASK_ROOT}/requirements.txt
COPY app ${LAMBDA_TASK_ROOT}/app
CMD ["app.main.handler"]
```

`docker-compose.yml` con servicios: `postgres` (postgis/postgis:16-3.4, healthcheck `pg_isready`), `migrate` (job que corre migraciones + seeds y termina), `intake`, `dispatch`, `geospatial`, `notification`, `gateway`, `frontend`. Todos los servicios dependen de `migrate` con `condition: service_completed_successfully`. Volumen nombrado para los datos de Postgres. Bind mount del código para hot reload en desarrollo.

`Makefile` con: `make up`, `make down`, `make logs`, `make test`, `make seed`, `make reset` (borra volumen y recrea).

---

## 9. Frontend

Rutas:

- `/` — Formulario del ciudadano. Selector de tipo de emergencia → el formulario cambia sus campos según el tipo (los `details` de §5.1). Selector de ciudad. Mapa Leaflet donde se hace clic para fijar la ubicación (con centro por defecto según la ciudad elegida). Al enviar, muestra el ID, la prioridad asignada y el estado.
- `/track/:id` — Seguimiento de una emergencia por el ciudadano.
- `/operator` — Dashboard del operador: tabla de emergencias activas (ID, tipo, prioridad con color, ciudad, estado, recurso asignado, tiempo transcurrido), filtros por ciudad/prioridad/estado, y mapa Leaflet con los marcadores de emergencias, recursos y círculos de hotspots. Botones para asignar recurso manualmente (`GET /v1/resources/nearby` + `POST /v1/dispatches`) y para cambiar el estado del despacho.
- `/login` — placeholder en fase local; se conecta a Supabase Auth en la fase 2.

Detalles:
- Colores de prioridad: P1 rojo, P2 naranja, P3 amarillo, P4 azul.
- TanStack Query con `refetchInterval` de 5 s en el dashboard durante la fase local; se sustituye por la suscripción Realtime en la fase 2.
- Toda llamada pasa por `src/lib/api.ts`, con `VITE_API_BASE_URL` (`http://localhost:8080` en local).
- Manejo explícito de estados de carga, vacío y error. Nada de pantallas en blanco.

---

## 10. Fases de ejecución

Ejecuta en este orden y **detente al final de cada fase para que yo verifique**.

### Fase 1 — Base
Repo, `docker-compose.yml`, Postgres+PostGIS, migraciones, seeds, Makefile, README. **DoD:** `make up` levanta la base y `make seed` carga recursos; se puede consultar `SELECT * FROM dispatch.resources`.

### Fase 2 — Intake
Servicio completo: schemas, triage con tests, repositorio, rutas, Dockerfile, health. **DoD:** `POST /v1/emergencies` con los 4 tipos devuelve la prioridad correcta y persiste; `pytest` verde.

### Fase 3 — Dispatch
`nearby` con PostGIS, asignación con bloqueo, auto-asignación, actualización de despacho. **DoD:** crear una emergencia P1 en Cali termina con un recurso asignado y la emergencia en `ASSIGNED`.

### Fase 4 — Geospatial + Notification
Consultas por zona, hotspots con clustering, notificaciones + SSE. **DoD:** los hotspots devuelven el cluster sembrado en Cali; cada cambio de estado deja fila en `notification.notifications`.

### Fase 5 — Gateway + Frontend
Nginx, formulario ciudadano, dashboard operador, mapas. **DoD:** el flujo end-to-end de §11 funciona en el navegador.

### Fase 6 — Supabase
Ver §12. **DoD:** la misma app corre apuntando a Supabase con RLS activo y el dashboard se actualiza por Realtime.

---

## 11. Prueba de aceptación end-to-end (la que hay que poder demostrar)

1. Abrir `http://localhost:3000`.
2. Crear: tipo **emergencia médica/rescate**, ciudad **Cali**, ubicación en el mapa, heridos **3**.
3. Enviar.
4. Intake recibe la emergencia.
5. Calcula **P1**.
6. Guarda: `#123, P1, CALI, TRIAGED`.
7. Dispatch busca recurso disponible.
8. Asigna **Ambulancia Cali 01**.
9. Geospatial procesa ubicación, zona y distancia.
10. Notification registra el cambio → `ASSIGNED`.
11. El dashboard del operador muestra la emergencia con P1, Cali, ASSIGNED y la ambulancia, y el marcador aparece en el mapa.

Escribe esta prueba también como script automatizado en `tests/e2e/test_flow.py` (usa `httpx` contra el gateway).

---

## 12. Supabase (fase 2)

**Crear el proyecto:**
1. Proyecto nuevo en supabase.com, región `us-east-1` (misma que se usará luego en AWS).
2. Guardar la cadena de conexión administrativa solo en AWS Secrets Manager. La URL y anon key públicas del frontend se configuran exclusivamente en el panel de Vercel. **Nunca** commitear ninguna.
3. Habilitar PostGIS: `CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;`
4. Aplicar `database/migrations/*` en orden (Supabase CLI: `supabase link` + `supabase db push`, o el SQL Editor). Deben correr sin cambios respecto a local — por eso son idempotentes.
5. Aplicar `database/seeds/*`.

**Auth y roles:** usar Supabase Auth (email/password). El rol se guarda en `raw_app_meta_data->>'role'` con valores `CITIZEN` u `OPERATOR`. Crea un helper SQL:
```sql
CREATE OR REPLACE FUNCTION auth.user_role() RETURNS text
LANGUAGE sql STABLE AS $$
  SELECT COALESCE(auth.jwt() -> 'app_metadata' ->> 'role', 'CITIZEN');
$$;
```

**RLS** (`database/rls/`), activando `ENABLE ROW LEVEL SECURITY` en todas las tablas:

| Tabla | Política |
|---|---|
| `intake.emergencies` | `INSERT`: cualquier usuario autenticado, forzando `citizen_id = auth.uid()`. `SELECT`: el ciudadano solo las suyas; el operador todas. `UPDATE`: solo `OPERATOR`. |
| `dispatch.resources` | `SELECT`/`UPDATE`: solo `OPERATOR`. |
| `dispatch.assignments` | `SELECT`/`INSERT`/`UPDATE`: solo `OPERATOR`. |
| `geo.hotspots` | `SELECT`: solo `OPERATOR`. |
| `notification.notifications` | `SELECT`: `OPERATOR`, o el ciudadano dueño de la emergencia asociada. |

Los microservicios se conectan con el rol de servicio (bypass de RLS) porque ya aplican autorización a nivel de aplicación; **el frontend usa la anon key y sí queda sujeto a RLS**. Documenta esto en `docs/seguridad.md`.

**Realtime:**
```sql
ALTER TABLE intake.emergencies REPLICA IDENTITY FULL;
ALTER TABLE notification.notifications REPLICA IDENTITY FULL;
ALTER PUBLICATION supabase_realtime ADD TABLE intake.emergencies;
ALTER PUBLICATION supabase_realtime ADD TABLE notification.notifications;
```
En el cliente JS hay que indicar el esquema explícitamente (`.schema('intake')`) porque las tablas no están en `public`. Verifica que el esquema esté expuesto en la configuración de la API del proyecto. En el dashboard, sustituye el `refetchInterval` por una suscripción que invalide la query de TanStack Query al recibir un cambio.

**Conmutación local ↔ Supabase:** una sola variable, `DATABASE_URL`. El código no debe distinguir entre ambos entornos. Deja documentado en el README cómo apuntar a uno u otro.

---

## 13. Preparación para AWS (solo dejarlo listo, no desplegar)

- `handler = Mangum(app)` al final de cada `main.py`.
- Nada de estado en memoria entre requests; nada de tareas de fondo que sobrevivan a la respuesta.
- En desarrollo, Docker Compose inyecta valores no sensibles. En Lambda, la configuración se lee al inicializar desde Parameter Store y los secretos desde Secrets Manager.
- Logs estructurados en JSON a stdout, con `request_id`, `service`, `level` (después los recoge CloudWatch).
- Un `/health` por servicio que verifique conectividad a base de datos.
- `infrastructure/` queda creado pero vacío, con un `.gitkeep`.

---

## 14. Qué NO hacer

- No fusionar servicios ni compartir un paquete de dominio común entre ellos (sí puedes duplicar utilidades pequeñas).
- No escribir desde un servicio en el esquema de otro (única excepción: lectura de `geospatial` sobre `intake.emergencies`).
- No cambiar rutas, nombres de campos, enums ni el formato de respuesta.
- No usar ORM sync ni `psycopg2` bloqueante.
- No commitear archivos `.env`, llaves de Supabase ni credenciales.
- La fase de AWS se documenta y valida en `docs/despliegue-produccion.md`; usa AppConfig, no CodeDeploy/Canary.

---

## 15. Entregables de esta etapa

1. Repositorio con frontend, 4 microservicios, Docker, base de datos y documentación.
2. `docker compose up --build` funcionando desde cero.
3. Proyecto de Supabase creado, con migraciones, RLS y Realtime aplicados.
4. `README.md` con: requisitos, cómo levantar, configuración segura, cómo correr los tests, cómo cambiar a Supabase, y la tabla de endpoints.
5. `docs/decisiones.md` con los trade-offs (lectura cruzada de geospatial, fallo silencioso en llamadas entre servicios, service role vs RLS).
6. Diagrama de arquitectura local en `docs/diagrams/` (Mermaid en el README también sirve).
