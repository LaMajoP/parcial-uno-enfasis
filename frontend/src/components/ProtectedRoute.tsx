/**
 * Guarda de ruta por sesión y por rol (§8.4: "Proteger la ruta /operator").
 *
 * Esto es una barrera de INTERFAZ, no de seguridad. Sirve para que un ciudadano
 * no aterrice en un dashboard vacío y confuso. La barrera real son las políticas
 * RLS: aunque alguien fuerce la ruta manipulando el estado de React, la base de
 * datos no le devolverá ni una fila. Ver docs/seguridad.md.
 */
import { Navigate, useLocation } from 'react-router-dom'
import type { Role } from '../lib/auth'
import { useAuth } from '../lib/auth'

export function ProtectedRoute({
  requireRole,
  children,
}: {
  /** Si se indica, además de sesión exige exactamente este rol. */
  requireRole?: Role
  children: React.ReactNode
}) {
  const { user, role, loading } = useAuth()
  const location = useLocation()

  // Sin este caso, en cada recarga de página se redirigiría a /login durante el
  // instante en que la sesión aún se está leyendo, expulsando a quien sí estaba
  // autenticado.
  if (loading) {
    return <div className="p-6 text-slate-600">Comprobando sesión…</div>
  }

  if (!user) {
    // `from` permite volver a donde se quería ir después de entrar.
    return (
      <Navigate to="/login" state={{ from: location.pathname }} replace />
    )
  }

  if (requireRole && role !== requireRole) {
    return <Forbidden required={requireRole} actual={role} />
  }

  return <>{children}</>
}

/** Pantalla explícita de acceso denegado: nada de páginas en blanco (§9 del spec). */
function Forbidden({
  required,
  actual,
}: {
  required: Role
  actual: Role | null
}) {
  return (
    <div className="mx-auto max-w-md space-y-4 p-6">
      <div className="rounded-lg border border-amber-200 bg-amber-50 p-4 text-sm text-amber-900">
        <p className="font-medium">No tienes acceso a esta sección</p>
        <p className="mt-1">
          Esta vista requiere el rol <strong>{required}</strong> y tu cuenta
          tiene <strong>{actual}</strong>.
        </p>
      </div>
      <a
        href="/"
        className="inline-block rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
      >
        Volver a reportar una emergencia
      </a>
    </div>
  )
}
