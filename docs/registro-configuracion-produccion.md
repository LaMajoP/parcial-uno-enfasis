# Registro de configuración de producción

Este anexo registra la configuración de producción declarada de forma
reproducible en el repositorio. No incluye contraseñas, ARN de secretos
completos, tokens ni valores de variables.

## 1. Identificadores públicos

| Elemento | Valor documentado | Fuente |
|---|---|---|
| Región AWS | `us-west-2` | `.github/workflows/backend-cd.yml` |
| Stack | `emergency-platform-prod` | Pipeline y `template.yaml` |
| API Gateway | `https://0mdz1txwdc.execute-api.us-west-2.amazonaws.com/prod` | [Evidencias](evidencias-entrega.md) |
| Stage | `prod` | `EmergencyApi.StageName` |

El API Gateway incluido arriba es una URL pública, no un secreto.

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
