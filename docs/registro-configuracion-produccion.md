# Registro de configuración de producción

Este anexo sirve como reporte de configuración para la entrega. Distingue lo
que está declarado de forma reproducible en el repositorio de lo que debe
verificarse y capturarse desde la consola. Nunca escribas contraseñas, ARN de
secretos completos, tokens ni valores de variables en este archivo.

## 1. Identificadores públicos

| Elemento | Valor documentado | Fuente | Verificación de entrega |
|---|---|---|---|
| Región AWS | `us-west-2` | `.github/workflows/backend-cd.yml` | Captura de CloudFormation o consola AWS. |
| Stack | `emergency-platform-prod` | Pipeline y `template.yaml` | Estado `UPDATE_COMPLETE`. |
| API Gateway | `https://0mdz1txwdc.execute-api.us-west-2.amazonaws.com/prod` | Instantánea de [evidencias](evidencias-entrega.md#1-instantánea-comprobada-de-producción) | `curl` a una ruta pública y captura de API Gateway. |
| Stage | `prod` | `EmergencyApi.StageName` | Captura de stages de API Gateway. |
| Frontend Vercel | **Completar URL pública** | Panel de Vercel | Deployment `Ready` de Production. |

El API Gateway incluido arriba es una URL pública, no un secreto. Si el stack se
recrea y AWS genera una URL diferente, actualiza este registro y el README antes
de la entrega.

## 2. Componentes que declara la infraestructura

| Área | Configuración declarada | Archivo fuente |
|---|---|---|
| Backend | Cuatro funciones Lambda de imagen OCI: Intake, Dispatch, Geospatial y Notification; alias `prod`. | `infrastructure/template.yaml` |
| Registro de imágenes | Cuatro repositorios ECR inmutables. | `infrastructure/bootstrap.yaml` |
| API | API Gateway REST regional, modelo de validación para creación de emergencia, CORS restrictivo y throttling de stage. | `infrastructure/template.yaml` |
| Protección de abuso | Web ACL con límite por IP. | `infrastructure/template.yaml` |
| Configuración | Parámetros SSM por servicio bajo `/emergency-platform/prod/services/*/runtime`. | `infrastructure/template.yaml` |
| Secretos | Un secreto precreado en Secrets Manager, leído mediante permiso mínimo por Lambda. | `infrastructure/template.yaml`, `services/*/app/secrets.py` |
| Feature Flags | Aplicación AppConfig, ambiente `prod`, perfil `intake-feature-flags` y bake de 5 minutos. | `infrastructure/template.yaml` |
| Observabilidad | X-Ray y alarmas CloudWatch de Intake, API 5xx y latencia. | `infrastructure/template.yaml` |
| Costos | Budget mensual USD 10, alertas 50 % real y 85 % forecast. | `infrastructure/template.yaml` |

## 3. Valores operativos que se pueden mostrar

Estos valores no son secretos y se pueden incluir en capturas o video:

| Configuración | Valor inicial documentado | Cómo se prueba |
|---|---|---|
| Flag `auto_dispatch_enabled` | Activa | Ver perfil AppConfig. |
| `enabled_cities` | `PEREIRA`, `MANIZALES` | Crear una emergencia de prueba en cada ciudad y revisar log de Intake. |
| Kill switch | `auto_dispatch_enabled = false` | El POST persiste la emergencia sin invocar Dispatch; no hay redeploy. |
| Circuit breaker | Abre tras 3 timeout/5xx; recuperación tras 60 s | Ejecutar prueba local o mostrar logs de prueba controlada. |
| Alarmas de API | 5xx ≥ 1 y latencia media > 1500 ms en 60 s | Consola CloudWatch. |
| Budget | USD 10 mensual; 50 % actual, 85 % forecast | Consola AWS Budgets. |

## 4. Roles y secretos: comprobación segura

La verificación debe probar la arquitectura sin revelar material sensible.

1. En **Secrets Manager**, muestra solo el nombre del secreto
   `emergency-platform/prod/database`, su estado y fecha de rotación si existe.
   No abras ni fotografíes `Secret value`.
2. En **IAM**, muestra que el rol de cada Lambda tiene únicamente
   `secretsmanager:GetSecretValue` para el secreto de base de datos,
   `ssm:GetParameter` para su propio parámetro y las invocaciones Lambda internas
   necesarias. Oculta ID de cuenta si la política institucional lo requiere.
3. En **CloudTrail Event history**, filtra por `GetSecretValue` o
   `GetParameter` y muestra el evento, el rol invocador y la hora; no muestres
   la petición ni el valor obtenido.
4. En **GitHub Environment `production`**, muestra solo los nombres de secrets
   y variables: `AWS_DEPLOY_ROLE_ARN`, `DATABASE_SECRET_ARN`,
   `BUDGET_ALERT_EMAIL` y `VERCEL_ORIGIN`.
5. En **Vercel → Environment Variables**, muestra únicamente los nombres
   `VITE_API_BASE_URL`, `VITE_SUPABASE_URL` y `VITE_SUPABASE_ANON_KEY` asociados
   al entorno Production. La clave anónima es pública, pero no hace falta
   exponerla en el video.

## 5. Comandos de verificación sin secretos

Ejecutar desde una sesión AWS autorizada. Los comandos consultan estado y no
modifican infraestructura:

```bash
aws cloudformation describe-stacks \
  --stack-name emergency-platform-prod \
  --region us-west-2 \
  --query 'Stacks[0].StackStatus' --output text

aws cloudwatch describe-alarms \
  --alarm-names emergency-intake-errors-prod emergency-api-5xx-prod emergency-api-latency-prod \
  --region us-west-2 \
  --query 'MetricAlarms[].{Nombre:AlarmName,Estado:StateValue}' --output table

aws budgets describe-budget \
  --account-id TU_ID_DE_CUENTA \
  --budget-name emergency-platform-monthly-prod \
  --query 'Budget.{Nombre:BudgetName,Limite:BudgetLimit,Periodo:TimeUnit}' \
  --output table
```

En el último comando reemplaza `TU_ID_DE_CUENTA` localmente; no guardes ese
identificador en capturas si no está permitido por la institución.

## 6. Control de cambios para la entrega

Antes de grabar el video o generar el PDF final, completar esta lista:

- [ ] La URL de Vercel se añadió a este documento y al informe técnico.
- [ ] La URL de API se verificó después del último despliegue.
- [ ] El stage continúa siendo `prod`.
- [ ] El origen Vercel configurado en GitHub coincide exactamente con CORS.
- [ ] Las tres alarmas están en `OK` o se documentó la causa de otro estado.
- [ ] El budget conserva límite USD 10 y ambas notificaciones.
- [ ] Ninguna captura muestra valores, tokens, contraseñas o cadenas de conexión.
