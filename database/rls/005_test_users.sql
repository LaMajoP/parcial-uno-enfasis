-- 005_test_users.sql
-- Asigna el rol a los usuarios de prueba y verifica que RLS realmente filtra.
--
-- ⚠ ANTES de correr este archivo, crea los dos usuarios a mano en el dashboard:
--      Authentication → Users → Add user → Create new user
--      (marca "Auto Confirm User" para no tener que confirmar el email)
--
--        ciudadano@demo.com   /  Demo1234!
--        operador@demo.com    /  Demo1234!
--
-- Supabase Auth no expone una forma soportada de crear usuarios por SQL (la
-- contrasena se cifra en la capa de Auth, no en Postgres), por eso ese paso es
-- manual. Lo que si se hace por SQL es ponerles el rol.

-- ── 1. Asignar el rol en app_metadata ───────────────────────────────────────
-- `||` fusiona el JSONB conservando lo que Supabase ya guarda ahi (provider,
-- providers). Sobreescribir el objeto entero romperia el login.
-- Idempotente: correrlo dos veces deja el mismo valor.
UPDATE auth.users
SET raw_app_meta_data = COALESCE(raw_app_meta_data, '{}'::jsonb)
                        || '{"role": "OPERATOR"}'::jsonb
WHERE email = 'operador@demo.com';

UPDATE auth.users
SET raw_app_meta_data = COALESCE(raw_app_meta_data, '{}'::jsonb)
                        || '{"role": "CITIZEN"}'::jsonb
WHERE email = 'ciudadano@demo.com';

-- ── 2. Dar dueno a parte de las emergencias de demo ─────────────────────────
-- Los seeds dejan `citizen_id` NULL, asi que el ciudadano de prueba no veria
-- ninguna y no se podria demostrar la politica "solo las mias". Le adjudicamos
-- 3 de las 21; las demas quedan sin dueno (solo visibles para el operador).
UPDATE intake.emergencies
SET citizen_id = (SELECT id FROM auth.users WHERE email = 'ciudadano@demo.com')
WHERE id IN (
    'e0000000-0000-4000-8000-000000000001',
    'e0000000-0000-4000-8000-000000000004',
    'e0000000-0000-4000-8000-000000000007'
);

-- ── 3. Comprobacion de que el rol quedo bien ────────────────────────────────
--   email                | rol
--   ciudadano@demo.com   | CITIZEN
--   operador@demo.com    | OPERATOR
SELECT email, raw_app_meta_data ->> 'role' AS rol
FROM auth.users
WHERE email IN ('ciudadano@demo.com', 'operador@demo.com')
ORDER BY email;


-- ════════════════════════════════════════════════════════════════════════════
-- 4. PRUEBA DE RLS  (ejecutar este bloque aparte, seleccionandolo entero)
--
-- Suplanta a cada usuario dentro de una transaccion que termina en ROLLBACK,
-- asi que no deja rastro. Es la evidencia para el informe: demuestra que la
-- base de datos filtra por si sola, sin depender del frontend.
--
-- Resultado esperado:
--     emergencias_que_ve_el_ciudadano = 3
--     recursos_que_ve_el_ciudadano    = 0
--     emergencias_que_ve_el_operador  = 21
--     recursos_que_ve_el_operador     = 20
-- ════════════════════════════════════════════════════════════════════════════

-- El orden de cada bloque es obligatorio: primero se fijan los claims (leyendo
-- auth.users como superusuario) y DESPUES se baja a `authenticated`. Al reves no
-- funciona, porque el rol `authenticated` no tiene permiso para leer auth.users.

BEGIN;

-- ── Como CIUDADANO ──────────────────────────────────────────────────────────
SELECT set_config(
    'request.jwt.claims',
    json_build_object(
        'sub',          (SELECT id FROM auth.users WHERE email = 'ciudadano@demo.com'),
        'role',         'authenticated',
        'app_metadata', json_build_object('role', 'CITIZEN')
    )::text,
    true
);
SET LOCAL ROLE authenticated;

SELECT 'CIUDADANO'                     AS actuando_como,
       (SELECT count(*) FROM intake.emergencies) AS emergencias_visibles,  -- 3
       (SELECT count(*) FROM dispatch.resources) AS recursos_visibles;     -- 0

-- ── Como OPERADOR ───────────────────────────────────────────────────────────
RESET ROLE;   -- volver a superusuario para poder leer auth.users otra vez
SELECT set_config(
    'request.jwt.claims',
    json_build_object(
        'sub',          (SELECT id FROM auth.users WHERE email = 'operador@demo.com'),
        'role',         'authenticated',
        'app_metadata', json_build_object('role', 'OPERATOR')
    )::text,
    true
);
SET LOCAL ROLE authenticated;

SELECT 'OPERADOR'                      AS actuando_como,
       (SELECT count(*) FROM intake.emergencies) AS emergencias_visibles,  -- 21
       (SELECT count(*) FROM dispatch.resources) AS recursos_visibles;     -- 20

RESET ROLE;
ROLLBACK;
