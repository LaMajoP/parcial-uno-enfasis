-- 003_enums.sql
-- Tipos enumerados. Los nombres y valores son contrato: no se modifican.
-- CREATE TYPE no soporta IF NOT EXISTS, por eso cada uno va en un DO block.
-- La comprobacion se ancla al esquema `public`: en Supabase puede existir un tipo
-- con el mismo nombre en otro esquema, y sin el filtro el enum nunca se crearia.

DO $$
BEGIN
    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public' AND t.typname = 'emergency_type') THEN
        CREATE TYPE emergency_type AS ENUM ('RESCUE','SHELTER','SUPPLIES','STRUCTURAL_DAMAGE');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public' AND t.typname = 'priority_type') THEN
        CREATE TYPE priority_type AS ENUM ('P1','P2','P3','P4');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public' AND t.typname = 'city_type') THEN
        CREATE TYPE city_type AS ENUM ('CHOCO','PEREIRA','CALI','MANIZALES');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public' AND t.typname = 'emergency_status') THEN
        CREATE TYPE emergency_status AS ENUM ('RECEIVED','TRIAGED','ASSIGNED','IN_PROGRESS','RESOLVED','CANCELLED');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public' AND t.typname = 'resource_type') THEN
        CREATE TYPE resource_type AS ENUM ('AMBULANCE','FIRE_BRIGADE','RESCUE_TEAM','CIVIL_DEFENSE','HUMANITARIAN_TEAM');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public' AND t.typname = 'resource_status') THEN
        CREATE TYPE resource_status AS ENUM ('AVAILABLE','ASSIGNED','UNAVAILABLE');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public' AND t.typname = 'assignment_status') THEN
        CREATE TYPE assignment_status AS ENUM ('ASSIGNED','ACCEPTED','IN_PROGRESS','COMPLETED','CANCELLED');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public' AND t.typname = 'notification_channel') THEN
        CREATE TYPE notification_channel AS ENUM ('REALTIME','WEBHOOK');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public' AND t.typname = 'notification_status') THEN
        CREATE TYPE notification_status AS ENUM ('PENDING','SENT','FAILED');
    END IF;

    IF NOT EXISTS (SELECT 1 FROM pg_type t JOIN pg_namespace n ON n.oid = t.typnamespace
                    WHERE n.nspname = 'public' AND t.typname = 'notification_event') THEN
        CREATE TYPE notification_event AS ENUM ('EMERGENCY_CREATED','STATUS_CHANGED','RESOURCE_ASSIGNED','HOTSPOT_DETECTED');
    END IF;
END
$$;
