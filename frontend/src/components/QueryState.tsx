/**
 * Estados de carga, vacío y error (§9: "Nada de pantallas en blanco").
 *
 * Están en un componente único para que ninguna vista pueda "olvidarse" de
 * pintar uno de los tres.
 */
import type { ReactNode } from 'react'
import { ApiError } from '../lib/api'

export function Loading({ label = 'Cargando…' }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 rounded-lg border border-slate-200 bg-white p-6 text-slate-600">
      <span
        className="h-4 w-4 animate-spin rounded-full border-2 border-slate-300 border-t-slate-600"
        aria-hidden
      />
      <span>{label}</span>
    </div>
  )
}

export function Empty({ children }: { children: ReactNode }) {
  return (
    <div className="rounded-lg border border-dashed border-slate-300 bg-slate-50 p-8 text-center text-slate-500">
      {children}
    </div>
  )
}

export function ErrorBox({
  error,
  onRetry,
}: {
  error: unknown
  onRetry?: () => void
}) {
  const isApiError = error instanceof ApiError
  const code = isApiError ? error.code : 'UNKNOWN'
  const message =
    error instanceof Error ? error.message : 'Ocurrió un error inesperado.'

  return (
    <div
      role="alert"
      className="rounded-lg border border-red-200 bg-red-50 p-4 text-red-800"
    >
      <p className="font-medium">No se pudo completar la operación</p>
      <p className="mt-1 text-sm">{message}</p>
      <p className="mt-2 font-mono text-xs text-red-600">{code}</p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-3 rounded-md bg-red-600 px-3 py-1.5 text-sm font-medium text-white hover:bg-red-700"
        >
          Reintentar
        </button>
      )}
    </div>
  )
}
