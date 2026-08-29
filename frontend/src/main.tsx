import React from 'react'
import ReactDOM from 'react-dom/client'
// La hoja de Leaflet va antes que la propia: sin ella los tiles se apilan en
// vez de formar la cuadrícula. Se importa aquí y no con @import en el CSS
// porque un @import debe preceder a cualquier otra regla, y las directivas de
// Tailwind ya ocupan ese sitio.
import 'leaflet/dist/leaflet.css'
import { App } from './App'
import './index.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)

// Service worker (§4.4). Se registra tras `load` para no competir por ancho de
// banda con el primer render: en una red degradada —el escenario del enunciado—
// adelantarlo retrasaría justo lo que la persona necesita ver primero.
//
// Un fallo aquí no rompe nada: la aplicación funciona igual, solo pierde el modo
// sin conexión. Por eso se registra en silencio y no se propaga el error.
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch((error) => {
      console.warn('[pwa] No se pudo registrar el service worker:', error)
    })
  })
}
