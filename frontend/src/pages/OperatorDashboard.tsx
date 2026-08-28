/** Dashboard del operador (§9, ruta `/operator`). */
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useMemo, useState } from 'react'
import { PriorityBadge, StatusBadge } from '../components/Badges'
import { OperatorMap } from '../components/OperatorMap'
import { Empty, ErrorBox, Loading } from '../components/QueryState'
import {
  createDispatch,
  getDispatches,
  getHotspots,
  getNearbyResources,
  getResources,
  getZoneEmergencies,
  updateDispatchStatus,
} from '../lib/api'
import {
  CITIES,
  CITY_LABELS,
  RESOURCE_TYPE_LABELS,
  STATUS_LABELS,
  elapsedSince,
} from '../lib/constants'
import {
  EMERGENCIES_TABLE,
  NOTIFICATIONS_TABLE,
  useRealtime,
} from '../lib/realtime'
import type { RealtimeStatus } from '../lib/realtime'
import type {
  City,
  Dispatch,
  DispatchStatus,
  EmergencyStatus,
  Priority,
  ZoneEmergency,
} from '../lib/types'

const PRIORITIES: Priority[] = ['P1', 'P2', 'P3', 'P4']
const STATUSES: EmergencyStatus[] = [
  'RECEIVED',
  'TRIAGED',
  'ASSIGNED',
  'IN_PROGRESS',
]

export function OperatorDashboard() {
  const queryClient = useQueryClient()
  const [city, setCity] = useState<City>('CALI')
  const [priority, setPriority] = useState<Priority | ''>('')
  const [status, setStatus] = useState<EmergencyStatus | ''>('')
  const [selected, setSelected] = useState<ZoneEmergency | null>(null)

  const emergencies = useQuery({
    queryKey: ['zone', city, priority, status],
    queryFn: () =>
      getZoneEmergencies(city, {
        priority: priority || undefined,
        status: status || undefined,
      }),
  })

  const hotspots = useQuery({
    queryKey: ['hotspots', city],
    queryFn: () => getHotspots(city),
  })

  const resources = useQuery({
    queryKey: ['resources', city],
    queryFn: () => getResources(city),
  })

  const dispatches = useQuery({
    queryKey: ['dispatches'],
    queryFn: getDispatches,
  })

  /** Despacho vivo de cada emergencia, para la columna "recurso asignado". */
  const dispatchByEmergency = useMemo(() => {
    const map = new Map<string, Dispatch>()
    for (const dispatch of dispatches.data ?? []) {
      if (dispatch.status !== 'COMPLETED' && dispatch.status !== 'CANCELLED') {
        map.set(dispatch.emergencyId, dispatch)
      }
    }
    return map
  }, [dispatches.data])

  const refreshAll = () => {
    queryClient.invalidateQueries({ queryKey: ['zone'] })
    queryClient.invalidateQueries({ queryKey: ['dispatches'] })
    queryClient.invalidateQueries({ queryKey: ['resources'] })
    queryClient.invalidateQueries({ queryKey: ['hotspots'] })
  }

  // Sustituye al sondeo de 5 s (§8.3). Se escuchan las dos tablas publicadas:
  // `emergencies` cubre altas y cambios de estado; `notifications` cubre los
  // avisos que genera Dispatch al asignar un recurso, que es lo que hace que la
  // columna "recurso asignado" se actualice sin que el operador toque nada.
  const realtimeStatus = useRealtime(
    [EMERGENCIES_TABLE, NOTIFICATIONS_TABLE],
    refreshAll,
  )

  const assign = useMutation({
    mutationFn: ({
      emergencyId,
      resourceId,
    }: {
      emergencyId: string
      resourceId: string
    }) => createDispatch(emergencyId, resourceId),
    onSuccess: refreshAll,
  })

  const changeDispatch = useMutation({
    mutationFn: ({ id, next }: { id: string; next: DispatchStatus }) =>
      updateDispatchStatus(id, next),
    onSuccess: refreshAll,
  })

  return (
    <div className="space-y-6 p-6">
      <header className="flex flex-wrap items-end justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold text-slate-900">
            Panel del operador
          </h1>
          <p className="mt-1 flex items-center gap-2 text-sm text-slate-600">
            <span>Emergencias activas en {CITY_LABELS[city]}.</span>
            <RealtimeIndicator status={realtimeStatus} />
          </p>
        </div>
        <div className="flex flex-wrap gap-3">
          <select
            value={city}
            onChange={(e) => setCity(e.target.value as City)}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            {CITIES.map((option) => (
              <option key={option} value={option}>
                {CITY_LABELS[option]}
              </option>
            ))}
          </select>
          <select
            value={priority}
            onChange={(e) => setPriority(e.target.value as Priority | '')}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Todas las prioridades</option>
            {PRIORITIES.map((option) => (
              <option key={option} value={option}>
                {option}
              </option>
            ))}
          </select>
          <select
            value={status}
            onChange={(e) => setStatus(e.target.value as EmergencyStatus | '')}
            className="rounded-md border border-slate-300 px-3 py-2 text-sm"
          >
            <option value="">Todos los estados activos</option>
            {STATUSES.map((option) => (
              <option key={option} value={option}>
                {STATUS_LABELS[option]}
              </option>
            ))}
          </select>
        </div>
      </header>

      {(assign.isError || changeDispatch.isError) && (
        <ErrorBox error={assign.error ?? changeDispatch.error} />
      )}

      <section>
        {hotspots.isError ? (
          <ErrorBox error={hotspots.error} onRetry={() => hotspots.refetch()} />
        ) : (
          <OperatorMap
            city={city}
            emergencies={emergencies.data ?? []}
            resources={resources.data ?? []}
            hotspots={hotspots.data ?? []}
            onSelect={setSelected}
          />
        )}
        <p className="mt-2 text-xs text-slate-500">
          Círculos: zonas de concentración · Círculos de color: emergencias por
          prioridad · Cuadrados: recursos
        </p>
      </section>

      <section className="space-y-3">
        <h2 className="text-lg font-semibold text-slate-900">
          Emergencias activas
        </h2>

        {emergencies.isPending && <Loading label="Cargando emergencias…" />}

        {emergencies.isError && (
          <ErrorBox
            error={emergencies.error}
            onRetry={() => emergencies.refetch()}
          />
        )}

        {emergencies.isSuccess && emergencies.data.length === 0 && (
          <Empty>
            No hay emergencias activas en {CITY_LABELS[city]} con estos filtros.
          </Empty>
        )}

        {emergencies.isSuccess && emergencies.data.length > 0 && (
          <div className="overflow-x-auto rounded-lg border border-slate-200">
            <table className="w-full text-left text-sm">
              <thead className="bg-slate-50 text-xs uppercase text-slate-500">
                <tr>
                  <th className="px-3 py-2">ID</th>
                  <th className="px-3 py-2">Tipo</th>
                  <th className="px-3 py-2">Prioridad</th>
                  <th className="px-3 py-2">Ciudad</th>
                  <th className="px-3 py-2">Estado</th>
                  <th className="px-3 py-2">Recurso asignado</th>
                  <th className="px-3 py-2">Transcurrido</th>
                  <th className="px-3 py-2">Acciones</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-100 bg-white">
                {emergencies.data.map((emergency) => {
                  const dispatch = dispatchByEmergency.get(emergency.id)
                  return (
                    <tr
                      key={emergency.id}
                      className={
                        selected?.id === emergency.id ? 'bg-amber-50' : undefined
                      }
                    >
                      <td className="px-3 py-2 font-mono text-xs">
                        {emergency.id.slice(0, 8)}
                      </td>
                      <td className="px-3 py-2">{emergency.type}</td>
                      <td className="px-3 py-2">
                        <PriorityBadge priority={emergency.priority} />
                      </td>
                      <td className="px-3 py-2">
                        {CITY_LABELS[emergency.city]}
                      </td>
                      <td className="px-3 py-2">
                        <StatusBadge status={emergency.status} />
                      </td>
                      <td className="px-3 py-2">
                        {dispatch ? (
                          <span>
                            {dispatch.resourceName}
                            <span className="block text-xs text-slate-500">
                              {RESOURCE_TYPE_LABELS[dispatch.resourceType]} ·{' '}
                              {dispatch.status}
                            </span>
                          </span>
                        ) : (
                          <span className="text-slate-400">Sin asignar</span>
                        )}
                      </td>
                      <td className="px-3 py-2 text-slate-600">
                        {elapsedSince(emergency.createdAt)}
                      </td>
                      <td className="px-3 py-2">
                        <div className="flex flex-wrap gap-2">
                          {!dispatch && (
                            <button
                              type="button"
                              onClick={() => setSelected(emergency)}
                              className="rounded-md bg-slate-900 px-2 py-1 text-xs font-medium text-white hover:bg-slate-700"
                            >
                              Asignar recurso
                            </button>
                          )}
                          {dispatch && dispatch.status === 'ASSIGNED' && (
                            <button
                              type="button"
                              disabled={changeDispatch.isPending}
                              onClick={() =>
                                changeDispatch.mutate({
                                  id: dispatch.id,
                                  next: 'IN_PROGRESS',
                                })
                              }
                              className="rounded-md border border-slate-300 px-2 py-1 text-xs hover:bg-slate-50"
                            >
                              Iniciar
                            </button>
                          )}
                          {dispatch && dispatch.status === 'IN_PROGRESS' && (
                            <button
                              type="button"
                              disabled={changeDispatch.isPending}
                              onClick={() =>
                                changeDispatch.mutate({
                                  id: dispatch.id,
                                  next: 'COMPLETED',
                                })
                              }
                              className="rounded-md border border-emerald-300 bg-emerald-50 px-2 py-1 text-xs text-emerald-800 hover:bg-emerald-100"
                            >
                              Completar
                            </button>
                          )}
                        </div>
                      </td>
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </section>

      {selected && !dispatchByEmergency.get(selected.id) && (
        <AssignPanel
          emergency={selected}
          onClose={() => setSelected(null)}
          onAssign={(resourceId) =>
            assign.mutate(
              { emergencyId: selected.id, resourceId },
              { onSuccess: () => setSelected(null) },
            )
          }
          pending={assign.isPending}
        />
      )}
    </div>
  )
}

/** Panel de asignación manual: busca recursos cercanos y despacha uno. */
function AssignPanel({
  emergency,
  onClose,
  onAssign,
  pending,
}: {
  emergency: ZoneEmergency
  onClose: () => void
  onAssign: (resourceId: string) => void
  pending: boolean
}) {
  const nearby = useQuery({
    queryKey: ['nearby', emergency.id],
    queryFn: () =>
      getNearbyResources(
        emergency.location.latitude,
        emergency.location.longitude,
      ),
  })

  return (
    <section className="rounded-lg border border-slate-300 bg-white p-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <h3 className="font-semibold text-slate-900">
            Asignar recurso a {emergency.type}
          </h3>
          <p className="font-mono text-xs text-slate-500">{emergency.id}</p>
        </div>
        <button
          type="button"
          onClick={onClose}
          className="text-sm text-slate-500 underline"
        >
          Cerrar
        </button>
      </div>

      <div className="mt-4">
        {nearby.isPending && <Loading label="Buscando recursos cercanos…" />}
        {nearby.isError && (
          <ErrorBox error={nearby.error} onRetry={() => nearby.refetch()} />
        )}
        {nearby.isSuccess && nearby.data.length === 0 && (
          <Empty>No hay recursos disponibles dentro de 10 km.</Empty>
        )}
        {nearby.isSuccess && nearby.data.length > 0 && (
          <ul className="divide-y divide-slate-100">
            {nearby.data.map((resource) => (
              <li
                key={resource.id}
                className="flex items-center justify-between gap-4 py-2"
              >
                <div>
                  <p className="font-medium text-slate-900">{resource.name}</p>
                  <p className="text-xs text-slate-500">
                    {RESOURCE_TYPE_LABELS[resource.type] ?? resource.type} ·{' '}
                    {(resource.distanceMeters / 1000).toFixed(2)} km
                  </p>
                </div>
                <button
                  type="button"
                  disabled={pending}
                  onClick={() => onAssign(resource.id)}
                  className="rounded-md bg-slate-900 px-3 py-1.5 text-sm font-medium text-white hover:bg-slate-700 disabled:bg-slate-400"
                >
                  {pending ? 'Asignando…' : 'Asignar'}
                </button>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  )
}

/**
 * Estado de la conexión Realtime, visible en pantalla.
 *
 * Con el sondeo, que la actualización dejara de funcionar era invisible: la
 * pantalla simplemente se quedaba quieta y parecía que no pasaba nada. Con un
 * websocket es peor, porque puede caerse en silencio. Mostrar el estado permite
 * distinguir "no hay emergencias nuevas" de "dejé de enterarme".
 */
function RealtimeIndicator({ status }: { status: RealtimeStatus }) {
  const config = {
    connecting: { color: 'bg-amber-400', label: 'Conectando…' },
    connected: { color: 'bg-emerald-500', label: 'En vivo' },
    error: { color: 'bg-red-500', label: 'Sin conexión en vivo' },
  }[status]

  return (
    <span className="inline-flex items-center gap-1.5 text-xs text-slate-500">
      <span
        className={`h-2 w-2 rounded-full ${config.color}`}
        aria-hidden
      />
      {config.label}
    </span>
  )
}
