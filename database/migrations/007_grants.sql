-- 007_grants.sql
-- Unica lectura cruzada permitida en toda la plataforma: el servicio `geospatial`
-- necesita leer intake.emergencies para agregar por zona y calcular hotspots.
-- Se concede con un rol dedicado y de SOLO LECTURA, no dando acceso al esquema entero.
-- Trade-off documentado en docs/decisiones.md.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = 'geo_reader') THEN
        CREATE ROLE geo_reader NOLOGIN;
    END IF;
END
$$;

GRANT USAGE  ON SCHEMA intake              TO geo_reader;
GRANT SELECT ON intake.emergencies         TO geo_reader;

-- Blindaje explicito: geo_reader no escribe en intake bajo ninguna circunstancia.
REVOKE INSERT, UPDATE, DELETE, TRUNCATE ON intake.emergencies FROM geo_reader;

-- El usuario con el que se conectan los servicios en local hereda el rol, de modo
-- que el permiso queda modelado igual que en Supabase (donde geospatial usara un
-- rol propio con este mismo grant).
DO $$
BEGIN
    EXECUTE format('GRANT geo_reader TO %I', current_user);
EXCEPTION
    WHEN OTHERS THEN
        RAISE NOTICE 'No se pudo conceder geo_reader a %: %', current_user, SQLERRM;
END
$$;
