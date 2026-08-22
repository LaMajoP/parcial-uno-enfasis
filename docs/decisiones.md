# Decisiones de arquitectura y trade-offs

Registro de las decisiones conscientes del proyecto: qué se eligió, contra qué se
comparó y qué se pierde. Se actualiza a medida que avanzan las fases.

---

## 1. Lectura cruzada de `geospatial` sobre `intake.emergencies`

**Contexto.** Cada microservicio es dueño de su propio esquema y ningún servicio
escribe en el esquema de otro. Pero `geospatial` tiene que agregar emergencias por
zona y calcular hotspots con PostGIS, y esos datos viven en `intake.emergencies`.

**Alternativas.**

| Opción | Costo |
|---|---|
| Duplicar las emergencias en el esquema `geo` vía eventos | Consistencia eventual, código de sincronización, doble almacenamiento |
| Pedir los datos a Intake por HTTP y agregar en memoria | Se pierde PostGIS: `ST_ClusterDBSCAN` habría que reimplementarlo en Python, y el volumen crece con la ciudad |
| **Lectura directa de solo lectura (elegida)** | Acoplamiento a nivel de esquema entre dos servicios |

**Decisión.** Se concede `SELECT` — y solo `SELECT` — sobre `intake.emergencies`
mediante el rol dedicado `geo_reader` (`database/migrations/007_grants.sql`). El
rol tiene revocados `INSERT/UPDATE/DELETE/TRUNCATE` de forma explícita.

**Por qué se acepta.** El clustering geoespacial es exactamente el trabajo que la
base de datos hace mejor que la aplicación, y duplicar el dato solo para respetar
la regla habría añadido un problema de consistencia real a cambio de una pureza
arquitectónica nominal.

**Límite.** Es la **única** lectura cruzada permitida en toda la plataforma.
Cualquier otra necesidad de datos ajenos se resuelve por HTTP.

---

## 2. Fallo silencioso en las llamadas entre servicios

**Contexto.** Al crear una emergencia, Intake dispara dos llamadas salientes: la
notificación `EMERGENCY_CREATED` y el auto-despacho.

**Decisión.** Ambas son *fire-and-forget* con timeout de 3 s. Si Notification o
Dispatch están caídos, se registra el fallo en el log y **el `POST /v1/emergencies`
responde `201` igual**.

**Por qué.** El reporte de una emergencia es el dato crítico del sistema: perderlo
porque un servicio secundario no responde es inaceptable. Es preferible una
emergencia registrada sin recurso asignado que una emergencia que nunca llegó.

**Costo asumido.** No hay reintentos ni cola: si el auto-despacho falla, la
emergencia queda en `TRIAGED` y el operador la asigna a mano desde el dashboard.
Eso es aceptable porque el dashboard es un camino de recuperación real y siempre
disponible. En AWS, este es el punto natural para una cola (SQS) con reintentos.

---

## 3. Los microservicios usan el service role; el frontend queda sujeto a RLS

**Contexto.** En la fase Supabase, las políticas RLS controlan quién ve qué.

**Decisión.** Los microservicios se conectan con el rol de servicio, que hace
bypass de RLS. El frontend usa la `anon key` y sí queda sujeto a las políticas.

**Por qué.** Los servicios ya aplican autorización a nivel de aplicación y
necesitan operaciones que ninguna política de usuario permitiría (Dispatch cambia
el estado de una emergencia que no es suya, Geospatial lee emergencias de todos los
ciudadanos). Aplicarles RLS encima obligaría a modelar cada servicio como un
usuario, duplicando la lógica de autorización en dos lugares.

**Costo asumido.** Un bug de autorización en un servicio no tiene una segunda
línea de defensa en la base de datos. Se mitiga manteniendo la superficie de los
endpoints internos (`/v1/internal/*`) fuera del API Gateway. Detalle en
`docs/seguridad.md`.

---

## 4. `dispatch.assignments.emergency_id` sin foreign key

`emergency_id` apunta a una fila de `intake.emergencies`, que vive en otro esquema
y pertenece a otro servicio. Una FK ahí ataría el ciclo de vida de los dos
servicios: no se podría migrar `intake` a otra base de datos sin romper `dispatch`.

La integridad la garantiza la orquestación (Dispatch solo asigna sobre una
emergencia que acaba de leer). El costo es que una emergencia borrada dejaría
asignaciones huérfanas — aceptable porque las emergencias no se borran, se
`CANCELLED`.

---

## 5. `location` se deriva en un trigger, no en la aplicación

`latitude`, `longitude` y `location GEOGRAPHY(POINT,4326)` son el mismo dato en dos
formas. Un trigger `BEFORE INSERT OR UPDATE` recalcula `location` siempre, así que
es imposible que queden desincronizados — ni desde la app, ni desde un seed, ni
desde un `UPDATE` manual en psql.

La alternativa (una columna generada) no es viable: PostGIS marca las funciones de
construcción de geografía como no inmutables.

---

## 6. Las migraciones son idempotentes y el mismo SQL corre en local y en Supabase

Todo el SQL usa `IF NOT EXISTS` o bloques `DO $$ … $$` con comprobación previa.
No hay una herramienta de migración con tabla de versiones.

**Por qué.** El requisito es que los mismos archivos se apliquen sin cambios en
Supabase (SQL Editor o `supabase db push`), donde no se controla el orden ni el
estado previo. La idempotencia da esa garantía sin depender de una herramienta.

**Costo asumido.** No hay `down migrations` ni historial de versiones aplicadas.
Para revertir se usa `make reset`. Es aceptable en un proyecto de este alcance;
en producción haría falta Alembic o el sistema de migraciones de Supabase CLI.
