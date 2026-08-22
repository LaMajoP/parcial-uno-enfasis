/**
 * Único punto de salida a la API.
 *
 * Todo pasa por el gateway (`VITE_API_BASE_URL`), nunca por los puertos de los
 * servicios. Cuando el gateway se sustituya por API Gateway en AWS, este archivo
 * no cambia: cambia la variable de entorno.
 */
import type {
  City,
  Dispatch,
  DispatchStatus,
  Emergency,
  EmergencyCreated,
  EmergencyStatus,
  EmergencyType,
  Hotspot,
  NearbyResource,
  Priority,
  Resource,
  ZoneEmergency,
} from './types'

const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8080'

/** Error de la API que conserva el código del contrato, no solo el mensaje. */
export class ApiError extends Error {
  constructor(
    readonly code: string,
    message: string,
    readonly status: number,
  ) {
    super(message)
    this.name = 'ApiError'
  }
}

type Envelope<T> =
  | { success: true; data: T }
  | { success: false; error: { code: string; message: string } }

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        'Content-Type': 'application/json',
        ...(init?.headers ?? {}),
      },
    })
  } catch {
    // fetch solo rechaza por fallo de red: el servidor no respondió siquiera.
    throw new ApiError(
      'NETWORK_ERROR',
      'No se pudo contactar con el servidor. ¿Está levantada la plataforma?',
      0,
    )
  }

  let body: Envelope<T>
  try {
    body = await response.json()
  } catch {
    throw new ApiError(
      'INVALID_RESPONSE',
      `El servidor respondió algo que no es JSON (HTTP ${response.status}).`,
      response.status,
    )
  }

  if (!body.success) {
    throw new ApiError(body.error.code, body.error.message, response.status)
  }
  return body.data
}

// ── Intake ──────────────────────────────────────────────────────────────────

export interface CreateEmergencyInput {
  type: EmergencyType
  city: City
  location: { latitude: number; longitude: number }
  details: Record<string, unknown>
}

export const createEmergency = (input: CreateEmergencyInput) =>
  request<EmergencyCreated>('/v1/emergencies', {
    method: 'POST',
    body: JSON.stringify(input),
  })

export const getEmergency = (id: string) =>
  request<Emergency>(`/v1/emergencies/${id}`)

export const updateEmergencyStatus = (id: string, status: EmergencyStatus) =>
  request<Emergency>(`/v1/emergencies/${id}/status`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })

// ── Geospatial ──────────────────────────────────────────────────────────────

export const getZoneEmergencies = (
  city: City,
  filters: { priority?: Priority; status?: EmergencyStatus } = {},
) => {
  const params = new URLSearchParams()
  if (filters.priority) params.set('priority', filters.priority)
  if (filters.status) params.set('status', filters.status)
  const query = params.toString()
  return request<ZoneEmergency[]>(
    `/v1/zones/${city}/emergencies${query ? `?${query}` : ''}`,
  )
}

export const getHotspots = (city: City, radiusMeters = 5000) =>
  request<Hotspot[]>(`/v1/zones/${city}/hotspots?radiusMeters=${radiusMeters}`)

// ── Dispatch ────────────────────────────────────────────────────────────────

export const getNearbyResources = (
  latitude: number,
  longitude: number,
  radiusMeters = 10000,
) =>
  request<NearbyResource[]>(
    `/v1/resources/nearby?latitude=${latitude}&longitude=${longitude}&radiusMeters=${radiusMeters}`,
  )

export const getResources = (city: City) =>
  request<Resource[]>(`/v1/resources?city=${city}`)

export const getDispatches = () => request<Dispatch[]>('/v1/dispatches')

export const createDispatch = (emergencyId: string, resourceId: string) =>
  request<Dispatch>('/v1/dispatches', {
    method: 'POST',
    body: JSON.stringify({ emergencyId, resourceId }),
  })

export const updateDispatchStatus = (id: string, status: DispatchStatus) =>
  request<Dispatch>(`/v1/dispatches/${id}`, {
    method: 'PATCH',
    body: JSON.stringify({ status }),
  })

// ── Notification ────────────────────────────────────────────────────────────

/** URL del stream SSE. En la fase Supabase la reemplaza una suscripción Realtime. */
export const notificationStreamUrl = () =>
  `${BASE_URL}/v1/notifications/stream`
