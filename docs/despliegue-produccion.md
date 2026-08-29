# Despliegue de producción y Feature Flags

Este proyecto usa la estrategia B del parcial: **AWS AppConfig + Kill Switch +
Circuit Breaker**. No usa AWS CodeDeploy ni tráfico Canary de Lambda.

## 1. Prerrequisitos fuera del repositorio

Antes del primer despliegue, crear en AWS Secrets Manager el secreto llamado
`emergency-platform/prod/database`. Su `SecretString` puede ser una URL de
PostgreSQL o un objeto JSON con la clave `database_url`. El valor nunca se pasa a
CloudFormation, GitHub ni Vercel.

En GitHub, configurar un entorno protegido llamado `production` y estos valores:

| Ubicación | Nombre | Uso |
|---|---|---|
| Secret | `AWS_DEPLOY_ROLE_ARN` | Rol OIDC de GitHub Actions para ECR y CloudFormation |
| Secret | `DATABASE_SECRET_ARN` | ARN del secreto de base de datos para la política IAM mínima |
| Secret | `BUDGET_ALERT_EMAIL` | Destino de las dos alertas de AWS Budgets |
| Variable | `VERCEL_ORIGIN` | URL HTTPS exacta del frontend desplegado |

El rol OIDC confía solo en el entorno `production` de este repositorio. Configura
las reglas de protección de ese entorno para permitir únicamente la rama `main`;
no se usan claves AWS de larga duración en GitHub.

## 2. Qué crea la plantilla

`infrastructure/bootstrap.yaml` crea los cuatro repositorios ECR inmutables.
`infrastructure/template.yaml` crea el API Gateway en `prod`, cuatro Lambdas de
imagen OCI, políticas IAM mínimas, WAF por IP, AppConfig, alarmas y el presupuesto
mensual de USD 10.

Antes del primer pipeline, crear la federación OIDC (una sola vez):

```bash
aws cloudformation deploy \
  --template-file infrastructure/github-oidc.yaml \
  --stack-name emergency-platform-github-oidc \
  --region us-west-2 \
  --capabilities CAPABILITY_NAMED_IAM

aws cloudformation describe-stacks \
  --stack-name emergency-platform-github-oidc \
  --region us-west-2 \
  --query "Stacks[0].Outputs[?OutputKey=='GitHubActionsDeployRoleArn'].OutputValue" \
  --output text
```

Registrar el valor resultante como el secreto de Actions
`AWS_DEPLOY_ROLE_ARN`. La confianza del rol acepta exclusivamente el entorno
`production` del repositorio `LaMajoP/parcial-uno-enfasis`; no acepta forks,
otros repositorios ni ejecuciones fuera de ese entorno.

Las configuraciones no secretas se crean en Parameter Store bajo
`/emergency-platform/prod/services/*/runtime`. Cada Lambda las lee en su cold
start. Las credenciales solo se leen desde Secrets Manager. Ningún valor de
negocio o secreto se define como variable de entorno en las Lambdas.

El pipeline [backend-cd.yml](../.github/workflows/backend-cd.yml) ejecuta tests,
valida SAM, compila las cuatro imágenes con target `lambda`, las publica en ECR y
actualiza CloudFormation al hacer push a `main`. Cuando el stack queda estable,
espera que la alarma de Intake llegue a `OK` y recién entonces despliega la versión
inicial de AppConfig; así el rollback automático no confunde el estado inicial
`INSUFFICIENT_DATA` con un error de la aplicación.

Si el primer stack queda en `ROLLBACK_COMPLETE`, inspeccionar primero su estado y
recursos. Solo entonces se puede eliminar **ese stack fallido** para volver a
crearlo; no borrar stacks en otro estado.

```bash
aws cloudformation describe-stacks \
  --stack-name emergency-platform-prod \
  --region us-west-2 \
  --query 'Stacks[0].StackStatus' --output text

aws cloudformation describe-stack-resources \
  --stack-name emergency-platform-prod --region us-west-2
```

## 3. Flags operativas

El perfil `emergency-platform / prod / intake-feature-flags` tiene estas flags:

| Flag | Comportamiento |
|---|---|
| `auto_dispatch_enabled` | Kill Switch global de la llamada Intake → Dispatch. Si está apagada, la emergencia se guarda y responde `201`, pero no invoca Dispatch. |
| `auto_dispatch_enabled.enabled_cities` | Segmentación geográfica. La versión inicial habilita Pereira y Manizales. |

Intake consulta AppConfig Data con el intervalo de polling indicado por AWS y
mantiene el último snapshot correcto. Una indisponibilidad de AppConfig no puede
rechazar un reporte ciudadano: durante un cold start sin snapshot, auto-despacho
queda desactivado de forma segura. Para apagar una dependencia con efecto inmediato,
editar la flag en la consola de AppConfig, crear una nueva versión y desplegarla
con la estrategia `emergency-flags-immediate-with-bake`; no ejecutar
`docker build`, `sam deploy` ni cambiar una Lambda.

La estrategia tiene un periodo de observación de cinco minutos y el ambiente de
AppConfig monitorea `emergency-intake-errors-prod`. Si esa alarma se activa
durante el despliegue de configuración, AppConfig revierte la configuración.

## 4. Circuit breaker

Cada entorno caliente de Intake mantiene un circuito por dependencia:

```text
CLOSED -- 3 timeout/5xx --> OPEN -- 60 s --> HALF_OPEN -- éxito --> CLOSED
                                     |             |
                                     +-- falla -----+
```

En `OPEN`, las llamadas a Dispatch o Notification se omiten de inmediato y se
registran como `circuit_state=OPEN`. La persistencia de la emergencia ocurre antes
de cualquier llamada saliente, por lo que nunca se pierde por un fallo secundario.
El Kill Switch es el control global; el circuito protege cada ejecución de Lambda
contra una dependencia que ya está fallando.

## 5. Evidencia para la demostración

1. Mostrar AppConfig con el rollout inicial solo para Pereira y Manizales.
2. Crear una emergencia en Pereira: CloudWatch registra el intento de
   auto-despacho y la asignación.
3. En una prueba controlada, provocar tres respuestas `5xx` o timeouts de
   Dispatch. Mostrar en los logs el circuito `OPEN`; el POST debe seguir
   respondiendo `201` porque la emergencia ya fue persistida.
4. Apagar `auto_dispatch_enabled` en AppConfig y desplegar esa configuración.
   Crear otra emergencia y mostrar que no hay invocación a Dispatch, sin nuevo
   build o despliegue de Lambda.
5. Reactivar la flag y, si se quiere demostrar rollback automático de
   configuración, provocar la alarma de errores durante el periodo de bake.
6. Capturar AWS Budgets con la alerta real al 50 %, la proyectada al 85 % y el
   correo de confirmación de la suscripción.

## 6. Verificación local antes de publicar

```bash
sam validate --template-file infrastructure/template.yaml --lint
rg -n 'CodeDeploy|DeploymentPreference|Canary|EnableCanary' infrastructure/template.yaml
make test
```

El segundo comando no debe producir salida. `AutoPublishAlias: prod` sí debe
permanecer cuatro veces: conserva los nombres de invocación privada ya usados por
los microservicios, pero no habilita CodeDeploy.
