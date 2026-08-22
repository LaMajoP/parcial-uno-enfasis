-- 001_extensions.sql
-- Extensiones requeridas. Idempotente: el mismo archivo corre en local y en Supabase.
--
-- Nota Supabase: alli PostGIS debe habilitarse antes en el esquema `extensions`
--   CREATE EXTENSION IF NOT EXISTS postgis WITH SCHEMA extensions;
-- Si ya esta habilitado, los CREATE EXTENSION de abajo son un no-op y NO lo mueven
-- de esquema. En local (imagen postgis/postgis) quedan en `public`.

CREATE EXTENSION IF NOT EXISTS postgis;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
