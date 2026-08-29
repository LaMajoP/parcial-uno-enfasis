# Evidencias de entrega — Parcial 1

Este documento separa la evidencia ya comprobada de la que debe capturarse desde
las consolas de GitHub, Vercel y Supabase. No incluir contraseñas, URLs de
conexión ni llaves en las capturas. El índice, nombre sugerido y control de cada
archivo externo están en [evidencias/README.md](evidencias/README.md); el
informe que explica la arquitectura es [informe-tecnico.md](informe-tecnico.md).

## 1. Instantánea comprobada de producción

Capturada el **2026-08-29 07:16 UTC**.

| Elemento | Evidencia comprobada |
|---|---|
| Stack CloudFormation | `emergency-platform-prod` en `UPDATE_COMPLETE` |
| API Gateway | `https://0mdz1txwdc.execute-api.us-west-2.amazonaws.com/prod` |
| Alias de Lambda | `intake:prod → 6`; `dispatch:prod → 8`; `geospatial:prod → 8`; `notification:prod → 8` |
| AppConfig | despliegue `1`, versión `1`, estado `COMPLETE` |
| Alarmas | `emergency-intake-errors-prod`, `emergency-api-5xx-prod` y `emergency-api-latency-prod` en `OK` |
| AWS Budget | `emergency-platform-monthly-prod`, límite de `USD 10` |
| Alertas de Budget | consumo real al `50%` y proyección al `85%` |

Las siguientes rutas respondieron `HTTP 200` tras el despliegue:

```text
GET /v1/dispatches
GET /v1/zones/PEREIRA/emergencies
GET /v1/notifications
GET /v1/emergencies/e0000000-0000-4000-8000-000000000013
```

Para repetir la comprobación de infraestructura:

```bash
aws cloudformation describe-stacks \
  --stack-name emergency-platform-prod \
  --region us-west-2 \
  --query 'Stacks[0].StackStatus' --output text

curl -i https://0mdz1txwdc.execute-api.us-west-2.amazonaws.com/prod/v1/dispatches
```

## 2. Evidencia en el repositorio

| Rúbrica | Archivos para mostrar |
|---|---|
| Cuatro microservicios OCI/Lambda | `services/*/Dockerfile`, `infrastructure/template.yaml` |
| API Gateway, CORS, throttling y WAF | `infrastructure/template.yaml` |
| Secretos y configuración dinámica con IAM mínimo | `services/*/app/secrets.py`, `services/*/app/config.py`, `infrastructure/template.yaml` |
| Feature Flags y circuit breaker | `services/intake/app/services/feature_flags.py`, `services/intake/app/clients/circuit_breaker.py` |
| RLS, PostGIS y Realtime | `database/migrations/`, `database/rls/`, `frontend/src/lib/realtime.ts` |
| Diagramas y decisiones | `docs/arquitectura-c4.md`, `docs/decisiones.md`, `docs/seguridad.md` |
| Informe técnico y registro de configuración | `docs/informe-tecnico.md`, `docs/registro-configuracion-produccion.md` |
| Inventario de capturas y video | `docs/evidencias/README.md` |
| CI/CD | `.github/workflows/backend-cd.yml` |
| Presupuesto y alarmas | `infrastructure/template.yaml`, sección `MonthlyCostBudget` |

## 3. Capturas obligatorias que debes obtener manualmente

### GitHub Actions

1. Abre **GitHub → Actions → Backend CI/CD**.
2. Abre la última ejecución verde del `push` a `main`.
3. Captura la vista donde se vean `Test and validate infrastructure` y `Build images and deploy backend` como exitosos.

### Vercel y frontend

1. Abre tu proyecto en **Vercel → Deployments**.
2. Captura el último deployment de producción en estado `Ready` y la URL pública.
3. Abre la URL y toma una captura de:
   - el formulario ciudadano;
   - el seguimiento de una emergencia creada;
   - `/operator` con el mapa y el tablero.
4. En **Settings → Environment Variables**, verifica que existan en `Production`:

   ```text
   VITE_API_BASE_URL
   VITE_SUPABASE_URL
   VITE_SUPABASE_ANON_KEY
   ```

   No captures los valores; basta con los nombres y el entorno `Production`.

### CORS

Sustituye `TU_URL_DE_VERCEL` y ejecuta esto desde tu terminal. La respuesta debe
incluir `access-control-allow-origin` con ese mismo dominio.

```bash
curl -i -X OPTIONS \
  https://0mdz1txwdc.execute-api.us-west-2.amazonaws.com/prod/v1/dispatches \
  -H 'Origin: TU_URL_DE_VERCEL' \
  -H 'Access-Control-Request-Method: GET'
```

Si no coincide, actualiza la variable `VERCEL_ORIGIN` del entorno `production`
en GitHub con la URL HTTPS exacta de Vercel, sin `/` final, y ejecuta de nuevo el
pipeline backend.

### Supabase: RLS, Realtime y PostGIS

En **Supabase → SQL Editor**, ejecuta las consultas siguientes y captura el
resultado. No muestres credenciales ni tokens.

```sql
-- RLS activo en las tablas de negocio.
SELECT schemaname, tablename, rowsecurity
FROM pg_tables
WHERE schemaname IN ('intake', 'dispatch', 'geo', 'notification')
ORDER BY schemaname, tablename;

-- Tablas publicadas para Realtime.
SELECT schemaname, tablename
FROM pg_publication_tables
WHERE pubname = 'supabase_realtime'
ORDER BY schemaname, tablename;

-- Extensión geoespacial instalada.
SELECT extname
FROM pg_extension
WHERE extname = 'postgis';
```

Después, abre dos pestañas autenticadas como operador, modifica un despacho en
una y captura cómo la otra se actualiza sin recargar. Esa es la evidencia visual
de Realtime.

### Feature Flags, kill switch y circuit breaker

1. En **AWS AppConfig**, abre `emergency-platform` → ambiente `prod` → perfil
   `intake-feature-flags`. Captura la configuración inicial: debe habilitar
   auto-despacho solo para `PEREIRA` y `MANIZALES`.
2. Crea una emergencia de prueba en Pereira desde el frontend. Captura la
   respuesta y el log de CloudWatch que muestra el intento de auto-despacho.
3. Para el kill switch, edita `auto_dispatch_enabled` a `false`, crea una nueva
   versión y despliega con la estrategia `emergency-flags-immediate-with-bake`.
   Crea otra emergencia: debe persistirse, pero CloudWatch debe mostrar que
   Dispatch fue omitido. Restaura la flag al terminar.
4. Para el circuit breaker, muestra la prueba automatizada local, que no altera
   producción:

   ```bash
   docker compose run --rm --entrypoint pytest intake -q tests/test_circuit_breaker.py
   ```

   Para una demostración en producción se requiere una ventana controlada de
   fallas sintéticas; no conviene provocar fallas deliberadas en el ambiente que
   se usará para la entrega.

### AWS Budgets y CloudWatch

1. En **AWS Billing → Budgets**, abre `emergency-platform-monthly-prod` y toma
   una captura del límite de USD 10 y de las alertas `ACTUAL 50%` y
   `FORECASTED 85%`.
2. En **CloudWatch → Alarms**, captura las tres alarmas en estado `OK`.
3. Conserva el correo de confirmación de suscripción a Budgets. No generes gasto
   artificial solo para disparar las alertas.

## 4. Integridad del repositorio

Antes de entregar, ejecuta estas comprobaciones y captura el resultado vacío del
primer comando:

```bash
git ls-files | rg '(^|/)\.env($|\.)'
git log --all -G 'service_role|DATABASE_URL|postgresql://|postgres://' --oneline
git status --short
```

El último comando debe quedar vacío. Si un secreto real aparece en cualquier
historial, rótalo inmediatamente y pide ayuda para retirar el dato del historial
antes de compartir el repositorio.

## 5. Guion breve para el video (máximo 5 minutos)

El enunciado exige un video demostrativo, pero no obliga expresamente a que una
persona aparezca en cámara ni a que hable. Una narración breve mientras se
comparte pantalla es recomendable: permite explicar qué evidencia se observa sin
pasar el límite de tiempo. No mostrar secretos, paneles con valores o correos
personales.

1. **0:00–0:30:** C4 de contexto y contenedores; explicar los cuatro servicios.
2. **0:30–1:30:** frontend Vercel: crear y seguir una emergencia.
3. **1:30–2:15:** dashboard operador, mapa y actualización Realtime.
4. **2:15–3:00:** API Gateway, Lambdas OCI, CloudWatch y secretos dinámicos.
5. **3:00–4:10:** AppConfig: segmentación por ciudad y kill switch sin redeploy.
6. **4:10–5:00:** RLS/PostGIS, Budget, pipeline verde y cierre con las URLs de producción.

## 6. Límite funcional que la documentación no puede resolver

El frontend actual es React/Vite y funciona en Vercel, pero todavía no incluye
manifest, service worker ni cola de solicitudes offline. Para satisfacer de forma
estricta el requisito de "offline-first / PWA ligero", hay que implementar esa
capacidad antes de declarar la solución completamente terminada. Esta guía deja
la brecha explícita para no fabricar evidencia de un requisito no implementado;
no debe ocultarse en el video ni en el informe técnico.
