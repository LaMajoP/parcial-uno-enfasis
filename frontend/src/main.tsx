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
