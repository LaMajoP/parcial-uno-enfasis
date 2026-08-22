/**
 * Placeholder de autenticación (§9, ruta `/login`).
 *
 * En la fase local no hay login: el spec lo deja como placeholder y lo conecta a
 * Supabase Auth en la fase 6, con el rol (`CITIZEN` / `OPERATOR`) en
 * `raw_app_meta_data`. Esta pantalla existe para que la ruta ya esté en su sitio
 * y el cambio sea sustituir el cuerpo, no añadir routing.
 */
import { Link } from 'react-router-dom'

export function Login() {
  return (
    <div className="mx-auto max-w-md space-y-4 p-6">
      <h1 className="text-2xl font-semibold text-slate-900">Iniciar sesión</h1>
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-medium">Pendiente de la fase Supabase</p>
        <p className="mt-1">
          La autenticación se conecta a Supabase Auth en la fase 6. Mientras
          tanto, ambas vistas son de acceso libre.
        </p>
      </div>
      <div className="flex gap-3">
        <Link
          to="/"
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          Entrar como ciudadano
        </Link>
        <Link
          to="/operator"
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Entrar como operador
        </Link>
      </div>
    </div>
  )
}
