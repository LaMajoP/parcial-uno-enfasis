-- 004_realtime.sql
-- Activa Supabase Realtime en las dos tablas que el dashboard escucha (§8.3).
--
-- Realtime lee la replicacion logica de Postgres. Hacen falta dos cosas:
--   1. REPLICA IDENTITY FULL  -> que el WAL incluya la fila COMPLETA. Sin esto,
--      en un UPDATE llega solo la clave primaria y el cliente no puede saber si
--      la emergencia le corresponde ni que campo cambio.
--   2. Estar en la publicacion `supabase_realtime`.
--
-- Realtime RESPETA RLS: cada suscriptor recibe unicamente los cambios de las
-- filas que su politica de SELECT le deja ver. Por eso el orden importa — este
-- archivo va DESPUES del 003.
--
-- Idempotente: ALTER PUBLICATION ... ADD TABLE falla si la tabla ya esta, asi
-- que va condicionado a pg_publication_tables.

ALTER TABLE intake.emergencies         REPLICA IDENTITY FULL;
ALTER TABLE notification.notifications REPLICA IDENTITY FULL;

DO $$
BEGIN
    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
          AND schemaname = 'intake'
          AND tablename = 'emergencies'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE intake.emergencies;
    END IF;

    IF NOT EXISTS (
        SELECT 1 FROM pg_publication_tables
        WHERE pubname = 'supabase_realtime'
          AND schemaname = 'notification'
          AND tablename = 'notifications'
    ) THEN
        ALTER PUBLICATION supabase_realtime ADD TABLE notification.notifications;
    END IF;
END
$$;

-- Verificacion: deben salir exactamente estas dos filas.
--   SELECT schemaname, tablename FROM pg_publication_tables
--   WHERE pubname = 'supabase_realtime';
