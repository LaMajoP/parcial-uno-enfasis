-- 005_indexes.sql
-- Indices con nombre explicito para poder usar IF NOT EXISTS (idempotencia).
SET search_path = public, extensions;

CREATE INDEX IF NOT EXISTS emergencies_location_gist
    ON intake.emergencies USING GIST (location);
CREATE INDEX IF NOT EXISTS emergencies_city_status_priority
    ON intake.emergencies (city, status, priority);
CREATE INDEX IF NOT EXISTS emergencies_created_at_desc
    ON intake.emergencies (created_at DESC);

CREATE INDEX IF NOT EXISTS resources_location_gist
    ON dispatch.resources USING GIST (location);
CREATE INDEX IF NOT EXISTS resources_city_type_status
    ON dispatch.resources (city, type, status);

CREATE INDEX IF NOT EXISTS assignments_emergency_id
    ON dispatch.assignments (emergency_id);

CREATE INDEX IF NOT EXISTS notifications_emergency_created_at
    ON notification.notifications (emergency_id, created_at DESC);
