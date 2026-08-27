-- 002_enable_rls.sql
-- Activa Row Level Security y concede los privilegios base.
--
-- Dos mecanismos DISTINTOS que hay que aplicar los dos:
--
--   1. GRANT  -> decide si el rol puede tocar la tabla en absoluto.
--   2. RLS    -> decide QUE FILAS ve o modifica una vez tiene el GRANT.
--
-- Sin el GRANT, una politica RLS perfecta igual devuelve "permission denied":
-- nuestras tablas no estan en `public`, asi que NO heredan los grants por
-- defecto que Supabase le da a `anon` y `authenticated`. Este archivo los da
-- explicitamente; las politicas del 003 son las que realmente filtran.
--
-- `service_role` (el que usan los microservicios) hace BYPASS de RLS por
-- definicion: autoriza a nivel de aplicacion. Ver docs/seguridad.md.
--
-- Idempotente: ENABLE ROW LEVEL SECURITY y GRANT se pueden repetir sin error.

-- ── 1. Acceso a los esquemas ────────────────────────────────────────────────
-- USAGE solo abre la puerta del esquema; no da acceso a ninguna tabla.
GRANT USAGE ON SCHEMA intake       TO anon, authenticated;
GRANT USAGE ON SCHEMA dispatch     TO anon, authenticated;
GRANT USAGE ON SCHEMA geo          TO anon, authenticated;
GRANT USAGE ON SCHEMA notification TO anon, authenticated;

-- ── 2. Activar RLS ──────────────────────────────────────────────────────────
-- Desde este punto, sin politica que lo permita, NADIE (salvo service_role)
-- ve ni una fila. El default es denegar.
ALTER TABLE intake.emergencies              ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch.resources              ENABLE ROW LEVEL SECURITY;
ALTER TABLE dispatch.assignments            ENABLE ROW LEVEL SECURITY;
ALTER TABLE geo.hotspots                    ENABLE ROW LEVEL SECURITY;
ALTER TABLE notification.notifications      ENABLE ROW LEVEL SECURITY;

-- ── 3. Privilegios de tabla para el usuario autenticado ─────────────────────
-- El alcance real lo recortan las politicas del 003. Aqui solo se habilita el
-- verbo; no se concede DELETE en ninguna tabla a proposito: una emergencia se
-- CANCELA (cambio de estado), nunca se borra, porque es evidencia operativa.
GRANT SELECT, INSERT, UPDATE ON intake.emergencies         TO authenticated;
GRANT SELECT, UPDATE         ON dispatch.resources         TO authenticated;
GRANT SELECT, INSERT, UPDATE ON dispatch.assignments       TO authenticated;
GRANT SELECT                 ON geo.hotspots               TO authenticated;
GRANT SELECT                 ON notification.notifications TO authenticated;

-- ── 4. `anon` no recibe NADA ────────────────────────────────────────────────
-- Un visitante sin sesion no lee ni escribe emergencias. Se revoca de forma
-- explicita en vez de confiar en que no se concedio: si alguien anade un
-- `GRANT ... TO PUBLIC` mas adelante, esto lo neutraliza al volver a correr.
REVOKE ALL ON intake.emergencies         FROM anon;
REVOKE ALL ON dispatch.resources         FROM anon;
REVOKE ALL ON dispatch.assignments       FROM anon;
REVOKE ALL ON geo.hotspots               FROM anon;
REVOKE ALL ON notification.notifications FROM anon;
