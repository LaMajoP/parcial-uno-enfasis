/**
 * Aviso de estado de conexión y de reportes pendientes de envío.
 *
 * Sin esto, la cola offline sería invisible: la persona pulsaría enviar, no
 * pasaría nada aparente y volvería a intentarlo. El banner es lo que convierte
 * el mecanismo en algo que se entiende sin explicación.
 */
import { useEffect, useState } from 'react'
import { countPendingReports, flushQueue, onReconnect } from '../lib/offline'

export function OfflineBanner() {
  const [online, setOnline] = useState(navigator.onLine)
  const [pending, setPending] = useState(0)
  const [syncing, setSyncing] = useState(false)

  useEffect(() => {
    const refresh = () => countPendingReports().then(setPending)
    refresh()

    const goOffline = () => setOnline(false)

    const goOnline = async () => {
      setOnline(true)
      setSyncing(true)
      try {
        await flushQueue()
      } finally {
        setSyncing(false)
        refresh()
      }
    }

    window.addEventListener('offline', goOffline)
    const stopListening = onReconnect(goOnline)

    // El formulario avisa por un evento propio en vez de por props: el banner
    // vive en el layout y el formulario en una ruta, así que no hay forma
    // directa de pasarle un callback sin subir estado a toda la aplicación.
    window.addEventListener('queue-changed', refresh)

    return () => {
      window.removeEventListener('offline', goOffline)
      window.removeEventListener('queue-changed', refresh)
      stopListening()
    }
  }, [])

  // Todo en orden y nada pendiente: no se muestra nada. Un banner permanente de
  // "estás conectado" solo añade ruido.
  if (online && pending === 0) return null

  const tone = online
    ? 'border-sky-200 bg-sky-50 text-sky-900'
    : 'border-amber-200 bg-amber-50 text-amber-900'

  return (
    <div role="status" className={`border-b px-6 py-2 text-sm ${tone}`}>
      {!online && (
        <span className="font-medium">Sin conexión. </span>
      )}
      {pending > 0 ? (
        <span>
          {pending} {pending === 1 ? 'reporte guardado' : 'reportes guardados'} en
          este dispositivo.{' '}
          {syncing
            ? 'Enviando…'
            : online
              ? 'Se enviarán en un momento.'
              : 'Se enviarán al recuperar la conexión.'}
        </span>
      ) : (
        <span>Puedes reportar igualmente: se guardará y se enviará después.</span>
      )}
    </div>
  )
}
