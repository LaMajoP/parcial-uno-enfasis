/**
 * Cliente de Supabase para el navegador.
 *
 * Se usa SOLO para dos cosas (§8.3 y §8.4 de la guía):
 *   1. Autenticación (Supabase Auth).
 *   2. Suscripciones Realtime.
 *
 * Los DATOS no salen de aquí: van por REST a través del API Gateway
 * (`src/lib/api.ts`), según el flujo de la §9 — Frontend → API Gateway →
 * Lambda → Supabase.
 *
 * La llave que se usa es la `anon key`, que es pública por diseño: viaja dentro
 * del bundle JavaScript y cualquiera puede leerla. Lo que protege los datos no
 * es esconderla, sino las políticas RLS de `database/rls/`. Ver docs/seguridad.md.
 *
 * La `service_role key` NUNCA aparece en este archivo ni en ningún otro del
 * frontend: anularía el RLS por completo.
 */
import { createClient } from '@supabase/supabase-js'

const url = import.meta.env.VITE_SUPABASE_URL
const anonKey = import.meta.env.VITE_SUPABASE_ANON_KEY

/**
 * Si faltan las variables, no se lanza una excepción al importar: eso dejaría la
 * pantalla en blanco, y el spec (§9) lo prohíbe explícitamente. En su lugar se
 * expone esta bandera para que la UI muestre un aviso que se entienda.
 *
 * Ocurre cuando se compila sin configurar las variables en Vercel. Como las
 * `VITE_` se incrustan en tiempo de build, cambiarlas exige volver a desplegar.
 */
export const isSupabaseConfigured = Boolean(url && anonKey)

if (!isSupabaseConfigured) {
  console.error(
    '[supabase] Faltan VITE_SUPABASE_URL o VITE_SUPABASE_ANON_KEY. ' +
      'Configúralas en Vercel (Settings → Environment Variables) y redespliega.',
  )
}

/**
 * Con las variables ausentes se construye igual, contra un host inválido: así el
 * resto de la app importa este módulo sin romperse y los fallos se manifiestan
 * como errores de red en la pantalla de login, no como un módulo que no carga.
 */
export const supabase = createClient(
  url ?? 'https://sin-configurar.invalid',
  anonKey ?? 'sin-configurar',
  {
    auth: {
      // La sesión sobrevive a recargas y cambios de pestaña; el token se refresca
      // solo antes de expirar. Sin esto habría que volver a entrar cada hora.
      persistSession: true,
      autoRefreshToken: true,
      detectSessionInUrl: true,
    },
  },
)
