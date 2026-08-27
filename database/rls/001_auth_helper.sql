-- 001_auth_helper.sql
-- Helper de rol para las politicas RLS (§12 del spec).
--
-- El rol del usuario vive en `raw_app_meta_data->>'role'` de auth.users, con
-- valores CITIZEN u OPERATOR. Se usa `app_metadata` y NO `user_metadata` porque
-- `user_metadata` lo puede modificar el propio usuario desde el cliente: guardar
-- ahi el rol permitiria que cualquier ciudadano se auto-promoviera a operador.
--
-- Supabase copia `raw_app_meta_data` dentro del JWT, asi que `auth.jwt()` lo lee
-- sin tocar la tabla auth.users (importante: leer auth.users desde una politica
-- RLS provocaria recursion y consultas caras en cada fila).
--
-- Idempotente: CREATE OR REPLACE.

CREATE OR REPLACE FUNCTION auth.user_role()
RETURNS text
LANGUAGE sql
STABLE
AS $$
  SELECT COALESCE(auth.jwt() -> 'app_metadata' ->> 'role', 'CITIZEN');
$$;

COMMENT ON FUNCTION auth.user_role() IS
    'Devuelve CITIZEN u OPERATOR leyendo app_metadata del JWT. Por defecto CITIZEN (el menos privilegiado).';

-- Las politicas se evaluan con el rol `authenticated`, que necesita poder
-- ejecutar la funcion.
GRANT EXECUTE ON FUNCTION auth.user_role() TO authenticated, anon;
