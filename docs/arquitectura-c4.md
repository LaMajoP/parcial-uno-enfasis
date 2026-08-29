# Arquitectura C4

## Contexto

```mermaid
flowchart LR
    Citizen[Ciudadano] --> FE[Frontend Vercel PWA]
    Operator[Operador de emergencias] --> FE
    FE --> API[API Gateway prod + WAF]
    API --> Platform[Plataforma de gestión de emergencias]
    Platform --> Supabase[Supabase PostgreSQL/PostGIS + Realtime]
    Platform --> Agencies[Cruz Roja, Bomberos, Defensa Civil y UNGRD]
```

## Contenedores

```mermaid
flowchart TB
    FE[React/Vite en Vercel] --> API[API Gateway REST, stage prod]
    API --> IN[Intake & Triage Lambda OCI]
    API --> DI[Dispatch Lambda OCI]
    API --> GE[Geospatial Lambda OCI]
    API --> NO[Notification Lambda OCI]
    IN -->|invocación IAM privada| DI
    IN -->|invocación IAM privada| NO
    DI -->|invocación IAM privada| IN
    DI -->|invocación IAM privada| NO
    IN --> AC[AWS AppConfig]
    IN --> SSM[Parameter Store]
    DI --> SSM
    GE --> SSM
    NO --> SSM
    IN --> SM[Secrets Manager]
    DI --> SM
    GE --> SM
    NO --> SM
    IN --> DB[(Supabase PostgreSQL + PostGIS)]
    DI --> DB
    GE --> DB
    NO --> DB
```

## Componente crítico: Intake

```mermaid
flowchart LR
    Request[POST /v1/emergencies] --> Validation[FastAPI + esquema]
    Validation --> Triage[Triage determinista]
    Triage --> Store[Repositorio intake.emergencies]
    Store --> Commit[Commit]
    Commit --> Notify[Cliente Notification + circuit breaker]
    Commit --> Flags[AppConfig Feature Flags]
    Flags --> Dispatch[Cliente Dispatch + circuit breaker]
    Notify --> Response[201 Created]
    Dispatch --> Response
```

El commit precede las dependencias secundarias. Así, un Kill Switch, un circuito
abierto o una caída de Dispatch/Notification no elimina ni rechaza una solicitud
de auxilio.
