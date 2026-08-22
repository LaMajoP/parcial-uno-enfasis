-- 002_schemas.sql
-- Un esquema por microservicio. Ningun servicio escribe en el esquema de otro.

CREATE SCHEMA IF NOT EXISTS intake;
CREATE SCHEMA IF NOT EXISTS dispatch;
CREATE SCHEMA IF NOT EXISTS geo;
CREATE SCHEMA IF NOT EXISTS notification;

-- `auth` lo provee Supabase Auth. En local lo simulamos con una tabla minima.
-- En Supabase este bloque es un no-op porque auth.users ya existe.
CREATE SCHEMA IF NOT EXISTS auth;

-- Todo el bloque va condicionado a que la tabla NO exista: en Supabase auth.users
-- ya esta creada y no debe tocarse ni siquiera para ponerle un COMMENT (un
-- `COMMENT ON` suelto se ejecutaria igual y pisaria la metadata de la tabla real).
DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_tables WHERE schemaname = 'auth' AND tablename = 'users'
    ) THEN
        CREATE TABLE auth.users (
            id         UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email      VARCHAR(255) NOT NULL UNIQUE,
            role       VARCHAR(20)  NOT NULL DEFAULT 'CITIZEN',
            created_at TIMESTAMPTZ  NOT NULL DEFAULT now()
        );
        COMMENT ON TABLE auth.users IS
            'Simulacion local de Supabase Auth. En Supabase esta tabla ya existe y esta migracion no la crea.';
    END IF;
END
$$;
