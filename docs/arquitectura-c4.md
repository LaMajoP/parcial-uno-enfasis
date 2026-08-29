# Arquitectura C4

Este documento es el anexo de diagramas del informe técnico. Describe la
arquitectura objetivo de producción; el detalle operativo y la estrategia de
despliegue están en [despliegue-produccion.md](despliegue-produccion.md).

## Alcance y leyenda

- Las flechas continuas representan tráfico o invocaciones en tiempo de
  ejecución; las punteadas, lectura de configuración.
- **Ciudadano** y **operador** son los dos perfiles de usuario. Las cuatro
  ciudades atendidas son Chocó/Quibdó, Pereira, Cali y Manizales.
- Cada microservicio es propietario de su esquema lógico. La única lectura
  cruzada permitida es `geo` sobre `intake.emergencies`, mediante `geo_reader`
  de solo lectura; la decisión se justifica en
  [decisiones.md](decisiones.md#1-lectura-cruzada-de-geospatial-sobre-intakeemergencies).

## Nivel 1 — Contexto

```mermaid
flowchart LR
    Citizen[Ciudadano] -->|reporta y consulta estado| FE[Frontend React/Vite en Vercel]
    Operator[Operador de emergencias] -->|prioriza y despacha| FE
    FE -->|HTTPS| API[API Gateway REST: prod + WAF]
    API --> Platform[Plataforma de gestión de emergencias]
    Platform --> DB[(Supabase PostgreSQL + PostGIS)]
    FE -->|sesión y eventos RLS| SB[Supabase Auth + Realtime]
    Platform --> Agencies[Cruz Roja, Bomberos, Defensa Civil y UNGRD]
    Platform -. configuración .-> AWS[AWS Secrets Manager, Parameter Store y AppConfig]
```

La plataforma recibe solicitudes de rescate/médicas, albergue, suministros y
daño estructural. El triage produce prioridades P1 a P4 y el centro de despacho
coordina los recursos por ciudad. Supabase Auth y Realtime son servicios externos
de apoyo: el navegador usa una clave anónima pública y las políticas RLS siguen
siendo el límite de autorización.

## Nivel 2 — Contenedores

```mermaid
flowchart TB
    FE["Frontend React/Vite\nVercel Edge"] -->|HTTPS, CORS restrictivo| API["API Gateway REST\nstage prod"]
    API --> IN["Intake & Triage\nLambda OCI"]
    API --> DI["Dispatch & Resource Assignment\nLambda OCI"]
    API --> GE["Geospatial & Zone Aggregation\nLambda OCI"]
    API --> NO["Notification & Status Broadcast\nLambda OCI"]

    IN -->|lambda:InvokeFunction con IAM| DI
    IN -->|lambda:InvokeFunction con IAM| NO
    DI -->|lambda:InvokeFunction con IAM| IN
    DI -->|lambda:InvokeFunction con IAM| NO

    IN -. GetParameter .-> SSM["Parameter Store\nconfiguración no sensible"]
    DI -. GetParameter .-> SSM
    GE -. GetParameter .-> SSM
    NO -. GetParameter .-> SSM
    IN -. GetSecretValue .-> SM["Secrets Manager\nconexión de base de datos"]
    DI -. GetSecretValue .-> SM
    GE -. GetSecretValue .-> SM
    NO -. GetSecretValue .-> SM
    IN -. AppConfig Data .-> AC["AWS AppConfig\nkill switch y ciudades"]

    IN --> DB[("Supabase PostgreSQL\nPostGIS")]
    DI --> DB
    GE --> DB
    NO --> DB
```

| Contenedor | Responsabilidad | Datos propietarios | Interfaces públicas |
|---|---|---|---|
| Frontend | Formularios ciudadanos, seguimiento, mapa y tablero de operador | Estado de UI | Vercel; Supabase Auth/Realtime; API Gateway |
| Intake | Validación, persistencia y triage determinista | `intake.emergencies` | `POST/GET/PATCH /v1/emergencies` |
| Dispatch | Búsqueda y asignación transaccional de unidades | `dispatch.resources`, `dispatch.assignments` | `/v1/dispatches`, `/v1/resources` |
| Geospatial | Emergencias por ciudad y hotspots PostGIS | `geo.hotspots` | `/v1/zones/{city}/…` |
| Notification | Registro y difusión de cambios de estado | `notification.notifications` | `/v1/notifications` |

El frontend no llama directamente a las Lambdas ni a la base de datos para la
lógica operativa. Las rutas y contratos completos se documentan en el
[README](../README.md#endpoints).

## Nivel 3 — Componente crítico: Intake & Triage

```mermaid
flowchart LR
    Request["POST /v1/emergencies"] --> Validation["FastAPI + Pydantic\nvalidación de esquema"]
    Validation --> Triage["Triage determinista\nP1–P4"]
    Triage --> Store["Repositorio\nintake.emergencies"]
    Store --> Commit["Commit de la emergencia"]
    Commit --> Notify["Cliente Notification\nCircuit Breaker"]
    Commit --> Flags["AppConfig\nKill Switch + ciudades"]
    Flags --> Dispatch["Cliente Dispatch\nCircuit Breaker"]
    Notify --> Response["201 Created"]
    Dispatch --> Response
```

La persistencia ocurre antes de Notification y Dispatch. En consecuencia, una
dependencia secundaria caída, un circuito abierto o el kill switch no elimina ni
rechaza el reporte: la emergencia queda disponible para asignación manual.

## Vista de despliegue y controles transversales

```mermaid
flowchart LR
    DEV["Push a main"] --> CI["GitHub Actions\npruebas + SAM validate"]
    CI --> ECR["Amazon ECR\nimágenes OCI inmutables"]
    ECR --> CFN["CloudFormation/SAM"]
    CFN --> APIGW["API Gateway + WAF\nCORS y throttling"]
    CFN --> LAMBDA["4 Lambda con alias prod"]
    CFN --> OBS["CloudWatch alarmas\nErrors, 5XX, Latency"]
    CFN --> BUDGET["AWS Budget\nUSD 10"]
    LAMBDA --> CW["CloudWatch Logs JSON\nX-Ray"]
    VERCEL["Vercel\nproducción desde main"] --> FE["Frontend"]
```

- API Gateway aplica stage formal `prod`, CORS limitado al origen de Vercel y
  throttling. WAF añade límite por IP.
- Cada Lambda recibe permisos IAM mínimos únicamente para su parámetro, secreto
  y las invocaciones internas que necesita.
- CloudWatch monitorea errores de Intake, errores 5xx del gateway y latencia
  superior a 1500 ms. AWS Budgets alerta al 50 % real y 85 % proyectado del
  límite mensual.
- La estrategia elegida es **Feature Flags + Circuit Breakers**; el detalle y el
  flujo de rollback de configuración están en
  [despliegue-produccion.md](despliegue-produccion.md#3-flags-operativas).

## Estado documentado del requisito PWA

El frontend actual es React/Vite desplegable en Vercel y ofrece actualización
reactiva mediante Supabase Realtime. A la fecha del repositorio **no contiene
manifest, service worker ni cola de reportes offline**. Por tanto, esta
arquitectura no debe presentarse como PWA/offline-first hasta implementar esos
artefactos. Es una brecha funcional, no una brecha que pueda corregirse solo con
documentación; queda trazada en el [informe técnico](informe-tecnico.md#9-límites-y-pendientes-no-documentales).
