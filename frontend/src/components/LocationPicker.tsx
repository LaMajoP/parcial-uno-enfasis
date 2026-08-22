/**
 * Mapa donde el ciudadano fija la ubicación de su emergencia haciendo clic.
 */
import { MapContainer, Marker, TileLayer, useMapEvents } from 'react-leaflet'
import { useEffect } from 'react'
import { useMap } from 'react-leaflet'
import { CITY_CENTERS } from '../lib/constants'
import type { City, Location } from '../lib/types'
import { pickedIcon } from './MapMarkers'

function ClickHandler({ onPick }: { onPick: (location: Location) => void }) {
  useMapEvents({
    click(event) {
      onPick({ latitude: event.latlng.lat, longitude: event.latlng.lng })
    },
  })
  return null
}

/** Recentra el mapa cuando el usuario cambia de ciudad en el formulario. */
function RecenterOnCity({ city }: { city: City }) {
  const map = useMap()
  useEffect(() => {
    map.setView(CITY_CENTERS[city], 13)
  }, [city, map])
  return null
}

export function LocationPicker({
  city,
  value,
  onPick,
}: {
  city: City
  value: Location | null
  onPick: (location: Location) => void
}) {
  return (
    <div className="space-y-2">
      <div className="h-72 w-full overflow-hidden rounded-lg border border-slate-300">
        <MapContainer
          center={CITY_CENTERS[city]}
          zoom={13}
          className="h-full w-full"
          scrollWheelZoom
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
          />
          <RecenterOnCity city={city} />
          <ClickHandler onPick={onPick} />
          {value && (
            <Marker
              position={[value.latitude, value.longitude]}
              icon={pickedIcon()}
            />
          )}
        </MapContainer>
      </div>
      <p className="text-sm text-slate-500">
        {value ? (
          <>
            Ubicación seleccionada:{' '}
            <span className="font-mono">
              {value.latitude.toFixed(5)}, {value.longitude.toFixed(5)}
            </span>
          </>
        ) : (
          'Haz clic en el mapa para marcar dónde ocurre la emergencia.'
        )}
      </p>
    </div>
  )
}
