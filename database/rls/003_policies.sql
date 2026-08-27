-- 003_policies.sql
-- Politicas RLS, una por tabla y verbo, exactamente como la tabla de §12 del spec.
--
-- Como leer una politica:
--   USING       -> que filas EXISTENTES puede ver o tocar (SELECT/UPDATE/DELETE).
--   WITH CHECK  -> que filas puede DEJAR escritas (INSERT/UPDATE).
-- Un UPDATE necesita las dos: USING para poder alcanzar la fila, WITH CHECK para
-- que el resultado siga siendo legal. Sin WITH CHECK, un operador podria mover
-- una emergencia a otro ciudadano.
--
-- Idempotente: cada CREATE POLICY va precedido de DROP POLICY IF EXISTS.

-- ════════════════════════════════════════════════════════════════════════════
-- intake.emergencies
-- ════════════════════════════════════════════════════════════════════════════

-- INSERT: cualquier usuario autenticado puede reportar, pero SOLO a su nombre.
-- El WITH CHECK es lo que impide que un ciudadano cree emergencias firmadas por
-- otro: aunque el cliente mande otro citizen_id en el payload, la fila se rechaza.
DROP POLICY IF EXISTS emergencies_insert_own ON intake.emergencies;
CREATE POLICY emergencies_insert_own
    ON intake.emergencies
    FOR INSERT
    TO authenticated
    WITH CHECK (citizen_id = auth.uid());

-- SELECT: el ciudadano ve las suyas; el operador ve todas.
DROP POLICY IF EXISTS emergencies_select_own_or_operator ON intake.emergencies;
CREATE POLICY emergencies_select_own_or_operator
    ON intake.emergencies
    FOR SELECT
    TO authenticated
    USING (
        citizen_id = auth.uid()
        OR auth.user_role() = 'OPERATOR'
    );

-- UPDATE: solo el operador cambia estados. El ciudadano no puede marcar su
-- propia emergencia como RESOLVED ni subirle la prioridad.
DROP POLICY IF EXISTS emergencies_update_operator ON intake.emergencies;
CREATE POLICY emergencies_update_operator
    ON intake.emergencies
    FOR UPDATE
    TO authenticated
    USING (auth.user_role() = 'OPERATOR')
    WITH CHECK (auth.user_role() = 'OPERATOR');

-- Sin politica de DELETE: nadie borra emergencias por la anon key. Se cancelan.

-- ════════════════════════════════════════════════════════════════════════════
-- dispatch.resources
-- ════════════════════════════════════════════════════════════════════════════

-- El inventario de ambulancias y bomberos es informacion operativa: un ciudadano
-- no tiene por que saber donde esta cada recurso ni cual esta libre.
DROP POLICY IF EXISTS resources_select_operator ON dispatch.resources;
CREATE POLICY resources_select_operator
    ON dispatch.resources
    FOR SELECT
    TO authenticated
    USING (auth.user_role() = 'OPERATOR');

DROP POLICY IF EXISTS resources_update_operator ON dispatch.resources;
CREATE POLICY resources_update_operator
    ON dispatch.resources
    FOR UPDATE
    TO authenticated
    USING (auth.user_role() = 'OPERATOR')
    WITH CHECK (auth.user_role() = 'OPERATOR');

-- ════════════════════════════════════════════════════════════════════════════
-- dispatch.assignments
-- ════════════════════════════════════════════════════════════════════════════

DROP POLICY IF EXISTS assignments_select_operator ON dispatch.assignments;
CREATE POLICY assignments_select_operator
    ON dispatch.assignments
    FOR SELECT
    TO authenticated
    USING (auth.user_role() = 'OPERATOR');

DROP POLICY IF EXISTS assignments_insert_operator ON dispatch.assignments;
CREATE POLICY assignments_insert_operator
    ON dispatch.assignments
    FOR INSERT
    TO authenticated
    WITH CHECK (auth.user_role() = 'OPERATOR');

DROP POLICY IF EXISTS assignments_update_operator ON dispatch.assignments;
CREATE POLICY assignments_update_operator
    ON dispatch.assignments
    FOR UPDATE
    TO authenticated
    USING (auth.user_role() = 'OPERATOR')
    WITH CHECK (auth.user_role() = 'OPERATOR');

-- ════════════════════════════════════════════════════════════════════════════
-- geo.hotspots
-- ════════════════════════════════════════════════════════════════════════════

-- Los hotspots agregan emergencias de todos los ciudadanos: exponerlos al
-- ciudadano seria filtrar por agregacion lo que la politica de emergencies niega
-- fila a fila. Solo operador. Los escribe el servicio geospatial con service_role.
DROP POLICY IF EXISTS hotspots_select_operator ON geo.hotspots;
CREATE POLICY hotspots_select_operator
    ON geo.hotspots
    FOR SELECT
    TO authenticated
    USING (auth.user_role() = 'OPERATOR');

-- ════════════════════════════════════════════════════════════════════════════
-- notification.notifications
-- ════════════════════════════════════════════════════════════════════════════

-- El operador ve todo; el ciudadano ve las notificaciones de SUS emergencias.
-- El EXISTS cruza a intake.emergencies, que tambien tiene RLS: eso es deliberado
-- y refuerza la regla en vez de esquivarla — si el ciudadano no puede ver la
-- emergencia, el EXISTS da falso y tampoco ve su notificacion.
DROP POLICY IF EXISTS notifications_select_operator_or_owner ON notification.notifications;
CREATE POLICY notifications_select_operator_or_owner
    ON notification.notifications
    FOR SELECT
    TO authenticated
    USING (
        auth.user_role() = 'OPERATOR'
        OR EXISTS (
            SELECT 1
            FROM intake.emergencies e
            WHERE e.id = notifications.emergency_id
              AND e.citizen_id = auth.uid()
        )
    );

-- Las notificaciones SOLO las crea el servicio notification con service_role:
-- no hay politica de INSERT/UPDATE para `authenticated` a proposito.
