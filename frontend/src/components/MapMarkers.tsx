/**
 * Marcadores de Leaflet.
 *
 * Se usan `divIcon` en vez de los marcadores por defecto: los iconos PNG de
 * Leaflet se referencian por rutas relativas que los bundlers rompen, y además
 * un div permite pintar el marcador con el color de la prioridad sin generar
 * una imagen por cada una.
 */
import L from 'leaflet'
import { PRIORITY_COLORS } from '../lib/constants'
import type { Priority } from '../lib/types'

export function emergencyIcon(priority: Priority): L.DivIcon {
  const color = PRIORITY_COLORS[priority]
  return L.divIcon({
    className: '',
    html: `<div style="
      width:18px;height:18px;border-radius:9999px;
      background:${color};border:2px solid white;
      box-shadow:0 0 0 1px rgba(0,0,0,.25);
      display:flex;align-items:center;justify-content:center;
      color:white;font-size:9px;font-weight:700;font-family:system-ui"
      >${priority.slice(1)}</div>`,
    iconSize: [18, 18],
    iconAnchor: [9, 9],
  })
}

export function resourceIcon(): L.DivIcon {
  return L.divIcon({
    className: '',
    html: `<div style="
      width:14px;height:14px;
      background:#0f766e;border:2px solid white;
      box-shadow:0 0 0 1px rgba(0,0,0,.25)"
      ></div>`,
    iconSize: [14, 14],
    iconAnchor: [7, 7],
  })
}

export function pickedIcon(): L.DivIcon {
  return L.divIcon({
    className: '',
    html: `<div style="
      width:22px;height:22px;border-radius:9999px;
      background:rgba(220,38,38,.25);border:3px solid #dc2626"
      ></div>`,
    iconSize: [22, 22],
    iconAnchor: [11, 11],
  })
}
