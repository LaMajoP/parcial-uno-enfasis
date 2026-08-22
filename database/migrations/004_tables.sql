-- 004_tables.sql
-- `extensions` en el search_path para que GEOGRAPHY resuelva en Supabase
-- (en local PostGIS vive en public y el schema `extensions` simplemente se ignora).
SET search_path = public, extensions;

CREATE TABLE IF NOT EXISTS intake.emergencies (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    type       emergency_type   NOT NULL,
    priority   priority_type    NOT NULL,
    city       city_type        NOT NULL,
    status     emergency_status NOT NULL DEFAULT 'RECEIVED',
    latitude   DOUBLE PRECISION NOT NULL,
    longitude  DOUBLE PRECISION NOT NULL,
    location   GEOGRAPHY(POINT,4326) NOT NULL,
    details    JSONB            NOT NULL DEFAULT '{}',
    citizen_id UUID             NULL,
    created_at TIMESTAMPTZ      NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ      NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS dispatch.resources (
    id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name       VARCHAR(120)     NOT NULL,
    type       resource_type    NOT NULL,
    city       city_type        NOT NULL,
    status     resource_status  NOT NULL DEFAULT 'AVAILABLE',
    latitude   DOUBLE PRECISION NOT NULL,
    longitude  DOUBLE PRECISION NOT NULL,
    location   GEOGRAPHY(POINT,4326) NOT NULL,
    created_at TIMESTAMPTZ      NOT NULL DEFAULT now(),
    updated_at TIMESTAMPTZ      NOT NULL DEFAULT now()
);

-- emergency_id va SIN foreign key a proposito: cruza esquema y microservicio.
-- La integridad la garantiza la orquestacion, no la base de datos.
CREATE TABLE IF NOT EXISTS dispatch.assignments (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    emergency_id UUID              NOT NULL,
    resource_id  UUID              NOT NULL REFERENCES dispatch.resources(id),
    status       assignment_status NOT NULL DEFAULT 'ASSIGNED',
    assigned_at  TIMESTAMPTZ       NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ       NULL
);

CREATE TABLE IF NOT EXISTS geo.hotspots (
    id               UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    city             city_type     NOT NULL,
    center           GEOGRAPHY(POINT,4326) NOT NULL,
    radius_meters    INTEGER       NOT NULL,
    emergency_count  INTEGER       NOT NULL,
    highest_priority priority_type NOT NULL,
    generated_at     TIMESTAMPTZ   NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS notification.notifications (
    id           UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    emergency_id UUID                 NOT NULL,
    recipient_id UUID                 NULL,
    channel      notification_channel NOT NULL,
    event_type   notification_event   NOT NULL,
    payload      JSONB                NOT NULL DEFAULT '{}',
    status       notification_status  NOT NULL DEFAULT 'PENDING',
    created_at   TIMESTAMPTZ          NOT NULL DEFAULT now(),
    sent_at      TIMESTAMPTZ          NULL
);
