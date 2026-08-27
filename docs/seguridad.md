# Seguridad

Modelo de seguridad de la plataforma: quién puede ver y hacer qué, y dónde se
aplica cada control. Documento exigido por §8.2 de la guía de proyecto.

---

## 1. Los dos caminos hacia la base de datos

La misma base de datos de Supabase se alcanza por dos rutas con **niveles de
confianza distintos**, y esa es la decisión de diseño central:

```
Frontend (Vercel)  ──anon key──────────────►  Supabase  ◄── RLS ACTIVO
                                                  ▲
Microservicios (Lambda) ──service role key────────┘        RLS OMITIDO
```

| | Frontend | Microservicios |
|---|---|---|
| Llave | `anon key` (pública) | `service_role key` (secreta) |
| Dónde vive | Variable pública de Vercel, visible en el bundle | Secrets Manager, solo en memoria de la Lambda |
| RLS | **Sí aplica** | **Se omite** (bypass) |
| Quién autoriza | PostgreSQL, fila a fila | El código del servicio |

El frontend es código que se ejecuta en el navegador de una persona
desconocida: **cualquier cosa que lleve dentro es pública**, incluida la anon
key. Por eso el frontend nunca es la barrera de seguridad — la barrera es RLS
dentro de Postgres. Aunque alguien abra la consola del navegador, copie la anon
key y consulte Supabase directamente con `curl`, seguirá viendo únicamente sus
propias emergencias.

Los microservicios usan la `service_role key`, que **omite RLS por completo**.
Es correcto porque un microservicio no actúa en nombre de un usuario concreto:
`intake` necesita escribir emergencias de cualquier ciudadano y `geospatial`
necesita agregar todas las de una ciudad. La autorización de esos servicios se
aplica a nivel de aplicación, en su propio código.

**Regla no negociable:** la `service_role key` nunca sale del backend, nunca se
commitea y nunca se configura en Vercel. Si alguna vez llegara al navegador,
todo el modelo de seguridad de este documento quedaría anulado de golpe.

---

## 2. Roles

Dos roles, guardados en `raw_app_meta_data->>'role'` de `auth.users`:

| Rol | Quién es | Puede |
|---|---|---|
| `CITIZEN` | Persona que reporta una emergencia | Crear emergencias a su nombre y ver las suyas |
| `OPERATOR` | Personal de la central de emergencias | Ver todo, asignar recursos, cambiar estados |

El rol se lee con el helper `auth.user_role()`
(`database/rls/001_auth_helper.sql`), que lo saca del JWT.

### Por qué `app_metadata` y no `user_metadata`

Supabase tiene dos contenedores de metadatos en el usuario:

- `user_metadata` — **el propio usuario lo puede modificar** desde el cliente con
  `supabase.auth.updateUser()`.
- `app_metadata` — solo se modifica con la `service_role key` o desde SQL.

Guardar el rol en `user_metadata` significaría que cualquier ciudadano puede
ejecutar dos líneas en la consola del navegador y ascenderse a `OPERATOR`. Por
eso el rol vive en `app_metadata`, y por eso `auth.user_role()` devuelve
`CITIZEN` cuando no encuentra nada: **ante la duda, el privilegio mínimo**.

---

## 3. Políticas RLS

Definidas en `database/rls/003_policies.sql`. Al activar RLS el comportamiento
por defecto es **denegar**: una tabla sin políticas no devuelve ni una fila.

| Tabla | `CITIZEN` | `OPERATOR` |
|---|---|---|
| `intake.emergencies` | INSERT solo con `citizen_id = auth.uid()`; SELECT solo las suyas | SELECT y UPDATE de todas |
| `dispatch.resources` | — nada | SELECT y UPDATE |
| `dispatch.assignments` | — nada | SELECT, INSERT y UPDATE |
| `geo.hotspots` | — nada | SELECT |
| `notification.notifications` | SELECT de las de sus emergencias | SELECT de todas |

Decisiones que conviene justificar:

- **`WITH CHECK (citizen_id = auth.uid())` en el INSERT.** Es lo que impide
  suplantar a otro ciudadano. Aunque el cliente envíe otro `citizen_id` en el
  payload, Postgres rechaza la fila.
- **El ciudadano no ve `dispatch.resources`.** La posición y disponibilidad de
  ambulancias y bomberos es información operativa; publicarla permitiría deducir
  la cobertura de la ciudad en tiempo real.
- **Los hotspots son solo de operador.** Un hotspot es un agregado de
  emergencias ajenas. Dárselo al ciudadano filtraría por agregación justo lo que
  la política de `emergencies` niega fila a fila.
- **Nadie tiene `DELETE`.** Una emergencia es evidencia operativa: se cancela con
  un cambio de estado a `CANCELLED`, no se borra. El privilegio ni siquiera se
  concede.
- **`GRANT` y RLS son controles distintos y hacen falta los dos.** El `GRANT`
  decide si el rol puede tocar la tabla; RLS decide qué filas. Como las tablas no
  están en `public`, no heredan los grants por defecto de Supabase y hay que
  darlos explícitamente (`database/rls/002_enable_rls.sql`). A `anon` se le
  revoca todo: sin sesión iniciada no se lee ni se escribe nada.

---

## 4. Realtime también respeta RLS

`intake.emergencies` y `notification.notifications` están publicadas para
Supabase Realtime (`database/rls/004_realtime.sql`). Realtime evalúa las
políticas de `SELECT` para cada suscriptor, así que un ciudadano suscrito solo
recibe eventos de sus propias emergencias, no del resto.

Las tablas están en `REPLICA IDENTITY FULL` para que los `UPDATE` viajen con la
fila completa; con la identidad por defecto solo llegaría la clave primaria y el
cliente no podría ni evaluar si el cambio le corresponde.

---

## 5. Gestión de secretos

| Secreto | Dónde vive | Dónde **nunca** debe estar |
|---|---|---|
| `SUPABASE_SERVICE_ROLE_KEY` | AWS Secrets Manager | Repo, frontend, Vercel |
| `DATABASE_URL` (con contraseña) | AWS Secrets Manager | Repo, frontend, Vercel |
| `VITE_SUPABASE_ANON_KEY` | Variables de Vercel | — (es pública por diseño) |
| `VITE_SUPABASE_URL` | Variables de Vercel | — (es pública por diseño) |

`.env` está en `.gitignore`; `.env.example` solo contiene marcadores de posición.

Cualquier variable con prefijo `VITE_` **se incrusta en el bundle JavaScript** en
tiempo de build y acaba siendo pública. No es un descuido de configuración: es
cómo funciona Vite. Por eso solo pueden llevar ese prefijo la URL del proyecto y
la anon key.

---

## 6. Verificación

`database/rls/005_test_users.sql` incluye una prueba ejecutable que suplanta a
cada rol dentro de una transacción con `ROLLBACK` y cuenta las filas visibles:

| Actuando como | Emergencias visibles | Recursos visibles |
|---|---|---|
| `CITIZEN` | 3 (las suyas) | 0 |
| `OPERATOR` | 21 (todas) | 20 |

Antes de la entrega, revisar el historial completo de commits en busca de
secretos filtrados:

```bash
git log -p --all | grep -iE 'service_role|eyJhbGciOi|supabase.co:5432|password'
```
