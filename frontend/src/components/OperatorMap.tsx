/** Mapa del operador: emergencias, recursos y círculos de hotspots. */
import { Circle, MapContainer, Marker, Popup, TileLayer, useMap } from 'react-leaflet'
import { useEffect } from 'react'
import { CITY_CENTERS, PRIORITY_COLORS, RESOURCE_TYPE_LABELS } from '../lib/constants'
import type { City, Hotspot, Resource, ZoneEmergency } from '../lib/types'
import { emergencyIcon, resourceIcon } from './MapMarkers'

function RecenterOnCity({ city }: { city: City }) {
  const map = useMap()
  useEffect(() => {
    map.setView(CITY_CENTERS[city], 12)
  }, [city, map])
  return null
}

export function OperatorMap({
  city,
  emergencies,
  resources,
  hotspots,
  onSelect,
}: {
  city: City
  emergencies: ZoneEmergency[]
  resources: Resource[]
  hotspots: Hotspot[]
  onSelect: (emergency: ZoneEmergency) => void
}) {
  return (
    <div className="h-[28rem] w-full overflow-hidden rounded-lg border border-slate-300">
      <MapContainer
        center={CITY_CENTERS[city]}
        zoom={12}
        className="h-full w-full"
        scrollWheelZoom
      >
        <TileLayer
          attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
          url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        />
        <RecenterOnCity city={city} />

        {/* Los hotspots van primero para que queden por debajo de los marcadores. */}
        {hotspots.map((hotspot, index) => (
          <Circle
            key={`hotspot-${index}`}
            center={[hotspot.latitude, hotspot.longitude]}
            radius={hotspot.radiusMeters}
            pathOptions={{
              color: PRIORITY_COLORS[hotspot.highestPriority],
              fillColor: PRIORITY_COLORS[hotspot.highestPriority],
              fillOpacity: 0.12,
              weight: 2,
            }}
          >
            <Popup>
              <strong>Zona de concentración</strong>
              <br />
              {hotspot.emergencyCount} emergencias activas
              <br />
              Prioridad más alta: {hotspot.highestPriority}
            </Popup>
          </Circle>
        ))}

        {emergencies.map((emergency) => (
          <Marker
            key={emergency.id}
            position={[emergency.location.latitude, emergency.location.longitude]}
            icon={emergencyIcon(emergency.priority)}
            eventHandlers={{ click: () => onSelect(emergency) }}
          >
            <Popup>
              <strong>{emergency.type}</strong>
              <br />
              {emergency.priority} · {emergency.status}
              <br />
              <span className="font-mono text-xs">
                {emergency.id.slice(0, 8)}
              </span>
            </Popup>
          </Marker>
        ))}

        {resources.map((resource) => (
            <Marker
              key={resource.id}
              position={[resource.location.latitude, resource.location.longitude]}
              icon={resourceIcon()}
            >
              <Popup>
                <strong>{resource.name}</strong>
                <br />
                {RESOURCE_TYPE_LABELS[resource.type] ?? resource.type}
                <br />
                {resource.status}
              </Popup>
            </Marker>
          ))}
      </MapContainer>
    </div>
  )
}
