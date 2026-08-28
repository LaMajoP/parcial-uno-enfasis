/** Seguimiento de una emergencia por el ciudadano (§9, ruta `/track/:id`). */
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { PriorityBadge, StatusBadge } from '../components/Badges'
import { ErrorBox, Loading } from '../components/QueryState'
import { getEmergency } from '../lib/api'
import { CITY_LABELS, EMERGENCY_TYPE_LABELS, elapsedSince } from '../lib/constants'
import { useRealtime } from '../lib/realtime'
import type { EmergencyStatus } from '../lib/types'

const STEPS: EmergencyStatus[] = [
  'RECEIVED',
  'TRIAGED',
  'ASSIGNED',
  'IN_PROGRESS',
  'RESOLVED',
]

export function TrackEmergency() {
  const { id = '' } = useParams()
  const queryClient = useQueryClient()

  const query = useQuery({
    queryKey: ['emergency', id],
    queryFn: () => getEmergency(id),
  })

  // El ciudadano deja esta pantalla abierta esperando novedades. Se filtra por
  // `id` del lado servidor: sin el filtro, el navegador recibiría un evento por
  // CADA emergencia de la ciudad y volvería a pedir esta una y otra vez sin que
  // hubiera cambiado nada.
  //
  // El filtro es una optimización, no una medida de seguridad: quien decide qué
  // filas puede ver este usuario es la política RLS de intake.emergencies.
  useRealtime(
    [{ schema: 'intake', table: 'emergencies', filter: `id=eq.${id}` }],
    () => queryClient.invalidateQueries({ queryKey: ['emergency', id] }),
  )

  if (query.isPending) return <div className="p-6"><Loading /></div>
  if (query.isError) {
    return (
      <div className="mx-auto max-w-2xl space-y-4 p-6">
        <ErrorBox error={query.error} onRetry={() => query.refetch()} />
        <Link to="/" className="text-sm text-slate-600 underline">
          Volver al formulario
        </Link>
      </div>
    )
  }

  const emergency = query.data
  const currentStep = STEPS.indexOf(emergency.status)
  const cancelled = emergency.status === 'CANCELLED'

  return (
    <div className="mx-auto max-w-2xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">
          Seguimiento de tu emergencia
        </h1>
        <p className="mt-1 font-mono text-xs break-all text-slate-500">{id}</p>
      </header>

      <div className="rounded-lg border border-slate-200 bg-white p-6">
        <div className="flex flex-wrap items-center gap-3">
          <PriorityBadge priority={emergency.priority} />
          <StatusBadge status={emergency.status} />
          <span className="text-sm text-slate-500">
            reportada hace {elapsedSince(emergency.createdAt)}
          </span>
        </div>

        <dl className="mt-4 grid gap-3 text-sm sm:grid-cols-2">
          <div>
            <dt className="text-xs uppercase text-slate-500">Tipo</dt>
            <dd>{EMERGENCY_TYPE_LABELS[emergency.type]}</dd>
          </div>
          <div>
            <dt className="text-xs uppercase text-slate-500">Ciudad</dt>
            <dd>{CITY_LABELS[emergency.city]}</dd>
          </div>
          <div className="sm:col-span-2">
            <dt className="text-xs uppercase text-slate-500">Ubicación</dt>
            <dd className="font-mono text-xs">
              {emergency.location.latitude.toFixed(5)},{' '}
              {emergency.location.longitude.toFixed(5)}
            </dd>
          </div>
        </dl>
      </div>

      {cancelled ? (
        <div className="rounded-lg border border-slate-300 bg-slate-50 p-4 text-slate-600">
          Esta emergencia fue cancelada.
        </div>
      ) : (
        <ol className="space-y-2">
          {STEPS.map((step, index) => {
            const done = index <= currentStep
            return (
              <li key={step} className="flex items-center gap-3">
                <span
                  className={`h-3 w-3 rounded-full ${
                    done ? 'bg-emerald-500' : 'bg-slate-300'
                  }`}
                  aria-hidden
                />
                <span
                  className={done ? 'text-slate-900' : 'text-slate-400'}
                >
                  <StatusBadge status={step} />
                </span>
              </li>
            )
          })}
        </ol>
      )}

      <Link to="/" className="inline-block text-sm text-slate-600 underline">
        Reportar otra emergencia
      </Link>
    </div>
  )
}
