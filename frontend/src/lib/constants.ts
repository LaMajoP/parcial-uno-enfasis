import type { City, EmergencyType, Priority } from './types'

/** Centro de cada ciudad, para posicionar el mapa (§3.3 del spec). */
export const CITY_CENTERS: Record<City, [number, number]> = {
  CHOCO: [5.6947, -76.6611],
  PEREIRA: [4.8143, -75.6946],
  CALI: [3.4516, -76.532],
  MANIZALES: [5.0703, -75.5138],
}

export const CITY_LABELS: Record<City, string> = {
  CHOCO: 'Chocó (Quibdó)',
  PEREIRA: 'Pereira',
  CALI: 'Cali',
  MANIZALES: 'Manizales',
}

export const CITIES = Object.keys(CITY_LABELS) as City[]

export const EMERGENCY_TYPE_LABELS: Record<EmergencyType, string> = {
  RESCUE: 'Rescate o emergencia médica',
  SHELTER: 'Albergue',
  SUPPLIES: 'Suministros',
  STRUCTURAL_DAMAGE: 'Daños estructurales',
}

export const EMERGENCY_TYPES = Object.keys(
  EMERGENCY_TYPE_LABELS,
) as EmergencyType[]

/** Colores de prioridad del §9: P1 rojo, P2 naranja, P3 amarillo, P4 azul. */
export const PRIORITY_COLORS: Record<Priority, string> = {
  P1: '#dc2626',
  P2: '#ea580c',
  P3: '#ca8a04',
  P4: '#2563eb',
}

export const PRIORITY_CLASSES: Record<Priority, string> = {
  P1: 'bg-red-100 text-red-800 ring-red-600/30',
  P2: 'bg-orange-100 text-orange-800 ring-orange-600/30',
  P3: 'bg-yellow-100 text-yellow-800 ring-yellow-600/30',
  P4: 'bg-blue-100 text-blue-800 ring-blue-600/30',
}

export const STATUS_LABELS: Record<string, string> = {
  RECEIVED: 'Recibida',
  TRIAGED: 'Clasificada',
  ASSIGNED: 'Asignada',
  IN_PROGRESS: 'En curso',
  RESOLVED: 'Resuelta',
  CANCELLED: 'Cancelada',
}

export const RESOURCE_TYPE_LABELS: Record<string, string> = {
  AMBULANCE: 'Ambulancia',
  FIRE_BRIGADE: 'Bomberos',
  RESCUE_TEAM: 'Equipo de rescate',
  CIVIL_DEFENSE: 'Defensa Civil',
  HUMANITARIAN_TEAM: 'Equipo humanitario',
}

/** Tiempo transcurrido en formato corto, para la columna del dashboard. */
export function elapsedSince(iso: string): string {
  const minutes = Math.floor((Date.now() - new Date(iso).getTime()) / 60000)
  if (minutes < 1) return 'ahora'
  if (minutes < 60) return `${minutes} min`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours} h ${minutes % 60} min`
  return `${Math.floor(hours / 24)} d`
}
