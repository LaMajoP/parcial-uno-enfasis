/** Tipos del dominio, espejo de los enums de la API. */

export type EmergencyType =
  | 'RESCUE'
  | 'SHELTER'
  | 'SUPPLIES'
  | 'STRUCTURAL_DAMAGE'

export type Priority = 'P1' | 'P2' | 'P3' | 'P4'

export type City = 'CHOCO' | 'PEREIRA' | 'CALI' | 'MANIZALES'

export type EmergencyStatus =
  | 'RECEIVED'
  | 'TRIAGED'
  | 'ASSIGNED'
  | 'IN_PROGRESS'
  | 'RESOLVED'
  | 'CANCELLED'

export type ResourceType =
  | 'AMBULANCE'
  | 'FIRE_BRIGADE'
  | 'RESCUE_TEAM'
  | 'CIVIL_DEFENSE'
  | 'HUMANITARIAN_TEAM'

export type DispatchStatus =
  | 'ASSIGNED'
  | 'ACCEPTED'
  | 'IN_PROGRESS'
  | 'COMPLETED'
  | 'CANCELLED'

export interface Location {
  latitude: number
  longitude: number
}

export interface EmergencyCreated {
  id: string
  type: EmergencyType
  priority: Priority
  city: City
  status: EmergencyStatus
  createdAt: string
}

export interface Emergency extends EmergencyCreated {
  location: Location
  details: Record<string, unknown>
}

export interface ZoneEmergency {
  id: string
  type: EmergencyType
  priority: Priority
  city: City
  status: EmergencyStatus
  location: Location
  createdAt: string
}

export interface NearbyResource {
  id: string
  name: string
  type: ResourceType
  status: string
  distanceMeters: number
}

export interface Resource {
  id: string
  name: string
  type: ResourceType
  city: City
  status: string
  location: Location
}

export interface Dispatch {
  id: string
  emergencyId: string
  resourceId: string
  status: DispatchStatus
  assignedAt: string
  completedAt: string | null
  resourceName: string
  resourceType: ResourceType
  resourceStatus: string
}

export interface Hotspot {
  latitude: number
  longitude: number
  radiusMeters: number
  emergencyCount: number
  highestPriority: Priority
}
