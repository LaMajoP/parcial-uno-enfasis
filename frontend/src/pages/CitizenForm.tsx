/** Formulario del ciudadano (§9, ruta `/`). */
import { useMutation } from '@tanstack/react-query'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import { DetailsFields, initialDetails } from '../components/DetailsFields'
import type { DetailsState } from '../components/DetailsFields'
import { LocationPicker } from '../components/LocationPicker'
import { PriorityBadge, StatusBadge } from '../components/Badges'
import { ErrorBox } from '../components/QueryState'
import { createEmergency } from '../lib/api'
import {
  CITIES,
  CITY_CENTERS,
  CITY_LABELS,
  EMERGENCY_TYPES,
  EMERGENCY_TYPE_LABELS,
} from '../lib/constants'
import type { City, EmergencyType, Location } from '../lib/types'

export function CitizenForm() {
  const [type, setType] = useState<EmergencyType>('RESCUE')
  const [city, setCity] = useState<City>('CALI')
  const [location, setLocation] = useState<Location | null>(null)
  const [details, setDetails] = useState<DetailsState>(initialDetails('RESCUE'))

  const mutation = useMutation({ mutationFn: createEmergency })

  /** Cambiar de tipo reinicia `details`: los campos de un tipo no son válidos
   *  para otro, y enviarlos mezclados daría INVALID_PAYLOAD. */
  const changeType = (next: EmergencyType) => {
    setType(next)
    setDetails(initialDetails(next))
    mutation.reset()
  }

  const changeCity = (next: City) => {
    setCity(next)
    setLocation(null) // la ubicación anterior pertenecía a otra ciudad
  }

  const submit = (event: React.FormEvent) => {
    event.preventDefault()
    const point = location ?? {
      latitude: CITY_CENTERS[city][0],
      longitude: CITY_CENTERS[city][1],
    }
    mutation.mutate({ type, city, location: point, details })
  }

  if (mutation.isSuccess) {
    const created = mutation.data
    return (
      <div className="mx-auto max-w-2xl space-y-6 p-6">
        <div className="rounded-lg border border-emerald-200 bg-emerald-50 p-6">
          <h2 className="text-lg font-semibold text-emerald-900">
            Reporte recibido
          </h2>
          <p className="mt-1 text-sm text-emerald-800">
            Tu emergencia fue registrada y clasificada. Guarda este identificador
            para hacerle seguimiento.
          </p>

          <dl className="mt-4 grid gap-3 sm:grid-cols-2">
            <div>
              <dt className="text-xs uppercase text-slate-500">Identificador</dt>
              <dd className="font-mono text-sm break-all">{created.id}</dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">Prioridad</dt>
              <dd className="mt-1">
                <PriorityBadge priority={created.priority} />
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">Estado</dt>
              <dd className="mt-1">
                <StatusBadge status={created.status} />
              </dd>
            </div>
            <div>
              <dt className="text-xs uppercase text-slate-500">Ciudad</dt>
              <dd className="text-sm">{CITY_LABELS[created.city]}</dd>
            </div>
          </dl>

          <div className="mt-6 flex flex-wrap gap-3">
            <Link
              to={`/track/${created.id}`}
              className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white hover:bg-slate-700"
            >
              Seguir esta emergencia
            </Link>
            <button
              type="button"
              onClick={() => {
                mutation.reset()
                setLocation(null)
                setDetails(initialDetails(type))
              }}
              className="rounded-md border border-slate-300 px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Reportar otra
            </button>
          </div>
        </div>
      </div>
    )
  }

  return (
    <form onSubmit={submit} className="mx-auto max-w-2xl space-y-6 p-6">
      <header>
        <h1 className="text-2xl font-semibold text-slate-900">
          Reportar una emergencia
        </h1>
        <p className="mt-1 text-sm text-slate-600">
          Cuéntanos qué ocurre y dónde. La prioridad se asigna automáticamente.
        </p>
      </header>

      <div className="grid gap-4 sm:grid-cols-2">
        <label className="block">
          <span className="text-sm font-medium text-slate-700">
            Tipo de emergencia
          </span>
          <select
            value={type}
            onChange={(e) => changeType(e.target.value as EmergencyType)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          >
            {EMERGENCY_TYPES.map((option) => (
              <option key={option} value={option}>
                {EMERGENCY_TYPE_LABELS[option]}
              </option>
            ))}
          </select>
        </label>

        <label className="block">
          <span className="text-sm font-medium text-slate-700">Ciudad</span>
          <select
            value={city}
            onChange={(e) => changeCity(e.target.value as City)}
            className="mt-1 w-full rounded-md border border-slate-300 px-3 py-2"
          >
            {CITIES.map((option) => (
              <option key={option} value={option}>
                {CITY_LABELS[option]}
              </option>
            ))}
          </select>
        </label>
      </div>

      <section className="rounded-lg border border-slate-200 bg-white p-4">
        <h2 className="mb-3 text-sm font-semibold text-slate-900">
          Detalles de la situación
        </h2>
        <DetailsFields type={type} details={details} onChange={setDetails} />
      </section>

      <section>
        <h2 className="mb-2 text-sm font-semibold text-slate-900">Ubicación</h2>
        <LocationPicker city={city} value={location} onPick={setLocation} />
      </section>

      {mutation.isError && <ErrorBox error={mutation.error} />}

      <button
        type="submit"
        disabled={mutation.isPending}
        className="w-full rounded-md bg-red-600 px-4 py-3 font-semibold text-white hover:bg-red-700 disabled:cursor-not-allowed disabled:bg-slate-400"
      >
        {mutation.isPending ? 'Enviando…' : 'Enviar reporte'}
      </button>

      <p className="text-center text-xs text-slate-500">
        Si no marcas un punto en el mapa se usará el centro de la ciudad.
      </p>
    </form>
  )
}
