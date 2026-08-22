-- 006_triggers.sql
-- `location` NUNCA se escribe desde la aplicacion: se deriva siempre de
-- latitude/longitude aqui, para que no puedan quedar desincronizados.

CREATE OR REPLACE FUNCTION public.sync_location()
RETURNS TRIGGER
LANGUAGE plpgsql
SET search_path = public, extensions
AS $$
BEGIN
    NEW.location := ST_SetSRID(ST_MakePoint(NEW.longitude, NEW.latitude), 4326)::geography;
    RETURN NEW;
END;
$$;

CREATE OR REPLACE FUNCTION public.set_updated_at()
RETURNS TRIGGER
LANGUAGE plpgsql
AS $$
BEGIN
    NEW.updated_at := now();
    RETURN NEW;
END;
$$;

-- Sin `OF latitude, longitude`: el trigger tiene que dispararse en CUALQUIER
-- UPDATE. Si se limita a esas columnas, un `UPDATE ... SET location = ...` que no
-- las toque escribe una geografia arbitraria y deja los dos datos desincronizados.
DROP TRIGGER IF EXISTS emergencies_sync_location ON intake.emergencies;
CREATE TRIGGER emergencies_sync_location
    BEFORE INSERT OR UPDATE ON intake.emergencies
    FOR EACH ROW EXECUTE FUNCTION public.sync_location();

DROP TRIGGER IF EXISTS emergencies_set_updated_at ON intake.emergencies;
CREATE TRIGGER emergencies_set_updated_at
    BEFORE UPDATE ON intake.emergencies
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();

DROP TRIGGER IF EXISTS resources_sync_location ON dispatch.resources;
CREATE TRIGGER resources_sync_location
    BEFORE INSERT OR UPDATE ON dispatch.resources
    FOR EACH ROW EXECUTE FUNCTION public.sync_location();

DROP TRIGGER IF EXISTS resources_set_updated_at ON dispatch.resources;
CREATE TRIGGER resources_set_updated_at
    BEFORE UPDATE ON dispatch.resources
    FOR EACH ROW EXECUTE FUNCTION public.set_updated_at();
