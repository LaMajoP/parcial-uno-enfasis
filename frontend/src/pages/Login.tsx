/**
 * Autenticación real contra Supabase Auth (§8.4 de la guía).
 *
 * Sustituye al placeholder de la fase local. El rol (CITIZEN / OPERATOR) no se
 * elige aquí: viene de `app_metadata` del usuario y se asigna desde SQL
 * (`database/rls/005_test_users.sql`). Dejar que el cliente eligiera su rol
 * sería justamente el agujero que ese diseño evita.
 */
import { useState } from 'react'
import { Link, Navigate, useLocation, useNavigate } from 'react-router-dom'
import { useAuth } from '../lib/auth'
import { isSupabaseConfigured } from '../lib/supabase'

export function Login() {
  const { user, role, signIn, signOut, loading } = useAuth()
  const navigate = useNavigate()
  const location = useLocation()

  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)

  /** Ruta que el usuario intentaba abrir antes de que lo mandaran aquí. */
  const from = (location.state as { from?: string } | null)?.from

  if (loading) {
    return <div className="p-6 text-slate-600">Comprobando sesión…</div>
  }

  // Ya hay sesión: no tiene sentido mostrar el formulario. Se va a donde
  // quería ir, o al sitio que corresponda a su rol.
  if (user) {
    if (from) return <Navigate to={from} replace />
    return <SessionCard email={user.email ?? ''} role={role} onSignOut={signOut} />
  }

  const submit = async (event: React.FormEvent) => {
    event.preventDefault()
    setError(null)
    setSubmitting(true)
    try {
      const signedInRole = await signIn(email.trim(), password)
      // El destino depende del rol, y `signIn` lo devuelve porque el estado de
      // React todavía no se ha actualizado en este punto. Si venía redirigido
      // desde una ruta protegida, esa tiene prioridad.
      const destination =
        from ?? (signedInRole === 'OPERATOR' ? '/operator' : '/')
      navigate(destination, { replace: true })
    } catch (caught) {
      setError(caught instanceof Error ? caught.message : 'No se pudo iniciar sesión.')
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="mx-auto max-w-md space-y-4 p-6">
      <h1 className="text-2xl font-semibold text-slate-900">Iniciar sesión</h1>

      {!isSupabaseConfigured && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-4 text-sm text-red-900">
          <p className="font-medium">Supabase no está configurado</p>
          <p className="mt-1">
            Faltan <code>VITE_SUPABASE_URL</code> o{' '}
            <code>VITE_SUPABASE_ANON_KEY</code>. Configúralas en Vercel y vuelve
            a desplegar: estas variables se incrustan al compilar.
          </p>
        </div>
      )}

      <form onSubmit={submit} className="space-y-4">
        <div>
          <label
            htmlFor="email"
            className="block text-sm font-medium text-slate-700"
          >
            Correo
          </label>
          <input
            id="email"
            type="email"
            required
            autoComplete="email"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-900 focus:outline-none"
          />
        </div>

        <div>
          <label
            htmlFor="password"
            className="block text-sm font-medium text-slate-700"
          >
            Contraseña
          </label>
          <input
            id="password"
            type="password"
            required
            autoComplete="current-password"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-900 focus:outline-none"
          />
        </div>

        {error && (
          <div
            role="alert"
            className="rounded-md border border-red-200 bg-red-50 p-3 text-sm text-red-800"
          >
            {error}
          </div>
        )}

        <button
          type="submit"
          disabled={submitting}
          className="w-full rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700 disabled:opacity-50"
        >
          {submitting ? 'Entrando…' : 'Entrar'}
        </button>
      </form>

      <div className="rounded-lg border border-slate-200 bg-slate-50 p-4 text-sm text-slate-600">
        <p className="font-medium text-slate-700">Cuentas de prueba</p>
        <ul className="mt-1 space-y-0.5">
          <li>
            <code>ciudadano@demo.com</code> — ve solo sus emergencias
          </li>
          <li>
            <code>operador@demo.com</code> — acceso al dashboard
          </li>
        </ul>
      </div>
    </div>
  )
}

/** Vista cuando ya hay sesión abierta. */
function SessionCard({
  email,
  role,
  onSignOut,
}: {
  email: string
  role: string | null
  onSignOut: () => Promise<void>
}) {
  return (
    <div className="mx-auto max-w-md space-y-4 p-6">
      <h1 className="text-2xl font-semibold text-slate-900">Sesión iniciada</h1>
      <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-4 text-sm text-emerald-900">
        <p>
          Conectado como <strong>{email}</strong>
        </p>
        <p className="mt-1">
          Rol: <strong>{role}</strong>
        </p>
      </div>
      <div className="flex gap-3">
        <Link
          to={role === 'OPERATOR' ? '/operator' : '/'}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
        >
          {role === 'OPERATOR' ? 'Ir al dashboard' : 'Reportar una emergencia'}
        </Link>
        <button
          type="button"
          onClick={onSignOut}
          className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
        >
          Cerrar sesión
        </button>
      </div>
    </div>
  )
}
