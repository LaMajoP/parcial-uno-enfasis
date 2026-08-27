/// <reference types="vite/client" />

/**
 * Variables de entorno del frontend.
 *
 * Todas llevan prefijo `VITE_` porque es el único que Vite expone al navegador.
 * Eso significa que **se incrustan en el bundle y son públicas**: aquí solo
 * pueden ir valores que no importe que se lean (ver docs/seguridad.md).
 */
interface ImportMetaEnv {
  /** Gateway de la API. En local `http://localhost:8080`; en producción, API Gateway. */
  readonly VITE_API_BASE_URL?: string
  /** URL pública del proyecto de Supabase. */
  readonly VITE_SUPABASE_URL?: string
  /** Llave anónima de Supabase. Pública por diseño; los datos los protege RLS. */
  readonly VITE_SUPABASE_ANON_KEY?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
