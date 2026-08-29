# Inventario de evidencias externas

Esta carpeta reserva el lugar de las capturas y del enlace de video que exige el
parcial. Actualmente contiene solo esta guía: las imágenes deben provenir de las
consolas reales y no se deben fabricar ni editar para aparentar un despliegue.

Usa PNG o PDF legible, sin secretos. Si el docente recibe un enlace en vez de un
archivo, regístralo en la tabla de control al final.

## Nombres de archivos sugeridos

| Archivo a adjuntar | Qué debe mostrar | Estado al preparar el repo |
|---|---|---|
| `01-github-actions-verde.png` | Ejecución exitosa de **Backend CI/CD** en `main`: tests y deploy. | Captura externa pendiente. |
| `02-vercel-production.png` | Último deployment Vercel Production en `Ready` y URL. | Captura externa pendiente. |
| `03-frontend-ciudadano.png` | Formulario ciudadano y reporte creado. | Captura externa pendiente. |
| `04-frontend-seguimiento.png` | Seguimiento por identificador y estado. | Captura externa pendiente. |
| `05-dashboard-realtime-a.png` | Dashboard de operador antes de un cambio. | Captura externa pendiente. |
| `06-dashboard-realtime-b.png` | Segunda pestaña actualizada sin recarga tras el cambio. | Captura externa pendiente. |
| `07-api-gateway-cors.png` | Stage `prod`, ruta o respuesta OPTIONS con origen Vercel. | Captura externa pendiente. |
| `08-secrets-iam-cloudtrail.png` | Nombre del secreto, permiso mínimo y evento de lectura sin valor secreto. | Captura externa pendiente. |
| `09-supabase-rls-postgis.png` | Consulta que prueba RLS y extensión PostGIS. | Captura externa pendiente. |
| `10-supabase-realtime.png` | Tablas publicadas para Realtime. | Captura externa pendiente. |
| `11-appconfig-rollout.png` | Flags iniciales para Pereira y Manizales. | Captura externa pendiente. |
| `12-kill-switch-antes.png` | Auto-despacho habilitado: log o resultado de asignación. | Captura externa pendiente. |
| `13-kill-switch-despues.png` | Flag apagada: emergencia persistida y Dispatch omitido. | Captura externa pendiente. |
| `14-circuit-breaker-test.png` | Prueba automatizada del circuito o logs de entorno controlado. | Captura externa pendiente. |
| `15-cloudwatch-alarmas.png` | Alarmas de errores, 5xx y latencia. | Captura externa pendiente. |
| `16-aws-budget.png` | Límite USD 10 y alertas 50 % actual / 85 % forecast. | Captura externa pendiente. |
| `17-correo-budget.png` | Confirmación de suscripción a alertas de Budget. | Captura externa pendiente. |
| `18-integridad-repositorio.png` | Resultado de chequeos de `.env`, historial y árbol limpio. | Captura externa pendiente. |
| `19-video-demostrativo.txt` | Enlace no listado o institucional al video de máximo 5 minutos. | Enlace externo pendiente. |

No es obligatorio conservar estos nombres exactos, pero un orden fijo hace que el
evaluador encuentre rápidamente cada criterio de la rúbrica.

## Captura mínima por criterio

### Producción y CI/CD

1. Captura la ejecución verde de GitHub Actions posterior al último `push` a
   `main`.
2. Muestra ECR o las Lambdas OCI solo si se alcanza a leer el nombre y alias
   `prod`; evita exponer cuenta o URI si la política institucional lo prohíbe.
3. Para la API, usa una ruta GET y una preflight OPTIONS con el origen de Vercel.
   El comando está en [evidencias-entrega.md](../evidencias-entrega.md#cors).

### Datos y seguridad

1. Ejecuta las tres consultas SQL de RLS, Realtime y PostGIS de
   [evidencias-entrega.md](../evidencias-entrega.md#supabase-rls-realtime-y-postgis).
2. Muestra dos navegadores o perfiles autenticados para comprobar una
   actualización Realtime sin recargar.
3. Para secretos, no muestres el valor: una combinación de nombre del secreto,
   política IAM y evento CloudTrail basta para demostrar recuperación dinámica.

### Resiliencia y costos

1. Graba el estado inicial de AppConfig y una creación de emergencia en Pereira
   o Manizales que active auto-despacho.
2. Apaga `auto_dispatch_enabled`, publica la configuración y repite el reporte:
   debe guardarse, pero el log no debe invocar Dispatch. Vuelve a activarla al
   terminar. Esta es la evidencia de kill switch sin redeploy requerida por la
   opción B.
3. Captura las alarmas CloudWatch y el presupuesto con ambas notificaciones. No
   provoques gasto artificial para disparar avisos de costos.

## Datos que deben ocultarse

- Cualquier valor de Secrets Manager o Parameter Store.
- Contraseñas, `DATABASE_URL`, URI de Postgres, JWT y tokens de sesión.
- `SUPABASE_SERVICE_ROLE_KEY`, claves AWS, claves privadas y secretos de GitHub.
- Variables completas de Vercel; mostrar sus nombres es suficiente.

La URL pública del API Gateway y la clave anónima de Supabase no son secretos,
pero es preferible no mostrar valores innecesarios: reduce ruido y evita que una
captura incluya accidentalmente información sensible cercana.

## Control de evidencia final

Completar al generar la entrega; no marcar un elemento si no se adjuntó o enlazó
la prueba real.

| Evidencia | Archivo/enlace final | Revisado por | Fecha |
|---|---|---|---|
| CI/CD |  |  |  |
| Vercel y frontend |  |  |  |
| API Gateway y CORS |  |  |  |
| Secretos e IAM |  |  |  |
| RLS, PostGIS y Realtime |  |  |  |
| Feature Flags / Kill Switch / Circuit Breaker |  |  |  |
| CloudWatch y AWS Budget |  |  |  |
| Integridad del repositorio |  |  |  |
| Video |  |  |  |
