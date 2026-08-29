/**
 * Cola de reportes offline (§4.4: "módulo de radicación offline-first para
 * víctimas con conectividad intermitente").
 *
 * El caso real que resuelve: tras un sismo la red va y viene. Si el formulario
 * simplemente fallara, el reporte se perdería y la persona tendría que acordarse
 * de repetirlo. Aquí se guarda en el dispositivo y se reenvía solo.
 *
 * ── Por qué IndexedDB y no localStorage ─────────────────────────────────────
 * `localStorage` es síncrono (bloquea el hilo de la interfaz), guarda solo texto
 * y ronda los 5 MB. Un reporte lleva `details` anidados y, en daños
 * estructurales, una foto. IndexedDB es asíncrona y admite objetos y volúmenes
 * mucho mayores.
 *
 * ── Lo que esta cola NO hace ────────────────────────────────────────────────
 * No calcula la prioridad ni inventa un identificador. Ambos los produce el
 * servicio Intake al recibir el reporte: falsearlos en el cliente daría a la
 * persona un número que no existe en el sistema, que es peor que no darle
 * ninguno. Mientras el reporte está encolado se muestra como "pendiente de
 * envío", y solo cuando el servidor responde aparece su ID real.
 */
import type { CreateEmergencyInput } from './api'
import { createEmergency } from './api'

const DB_NAME = 'emergency-platform'
const DB_VERSION = 1
const STORE = 'pending-reports'

export interface PendingReport {
  /** Clave autoincremental de IndexedDB. La asigna el navegador. */
  id?: number
  input: CreateEmergencyInput
  /** Momento en que la persona pulsó enviar, no el de la sincronización. */
  queuedAt: string
}

function openDatabase(): Promise<IDBDatabase> {
  return new Promise((resolve, reject) => {
    const request = indexedDB.open(DB_NAME, DB_VERSION)
    request.onupgradeneeded = () => {
      const db = request.result
      if (!db.objectStoreNames.contains(STORE)) {
        db.createObjectStore(STORE, { keyPath: 'id', autoIncrement: true })
      }
    }
    request.onsuccess = () => resolve(request.result)
    request.onerror = () => reject(request.error)
  })
}

/** Envuelve una operación sobre el store para no repetir el baile de eventos. */
async function withStore<T>(
  mode: IDBTransactionMode,
  operation: (store: IDBObjectStore) => IDBRequest<T>,
): Promise<T> {
  const db = await openDatabase()
  try {
    return await new Promise<T>((resolve, reject) => {
      const request = operation(db.transaction(STORE, mode).objectStore(STORE))
      request.onsuccess = () => resolve(request.result)
      request.onerror = () => reject(request.error)
    })
  } finally {
    db.close()
  }
}

export async function enqueueReport(input: CreateEmergencyInput): Promise<void> {
  await withStore('readwrite', (store) =>
    store.add({ input, queuedAt: new Date().toISOString() }),
  )
}

export async function listPendingReports(): Promise<PendingReport[]> {
  return withStore<PendingReport[]>('readonly', (store) => store.getAll())
}

export async function countPendingReports(): Promise<number> {
  // IndexedDB puede no estar disponible (modo privado de algunos navegadores).
  // Se devuelve 0 en vez de propagar: la app debe seguir funcionando online.
  try {
    return await withStore<number>('readonly', (store) => store.count())
  } catch {
    return 0
  }
}

async function removeReport(id: number): Promise<void> {
  await withStore('readwrite', (store) => store.delete(id))
}

export interface FlushResult {
  sent: number
  failed: number
  /** IDs que devolvió el servidor, en el orden en que se enviaron. */
  ids: string[]
}

/**
 * Reenvía la cola en orden de llegada.
 *
 * Un reporte solo se borra si el servidor confirma; si falla, se queda para el
 * siguiente intento. El bucle NO se corta ante un fallo: un reporte con datos
 * inválidos bloquearía indefinidamente a todos los que van detrás.
 */
export async function flushQueue(): Promise<FlushResult> {
  const pending = await listPendingReports()
  const result: FlushResult = { sent: 0, failed: 0, ids: [] }

  for (const report of pending) {
    try {
      const created = await createEmergency(report.input)
      if (report.id !== undefined) await removeReport(report.id)
      result.sent += 1
      result.ids.push(created.id)
    } catch {
      result.failed += 1
    }
  }

  return result
}

/**
 * Registra el vaciado automático al recuperar conexión y devuelve la función
 * para dejar de escuchar.
 *
 * Se usa el evento `online` y no la Background Sync API a propósito: Background
 * Sync no existe en Safari/iOS, y buena parte de los reportes ciudadanos llegan
 * desde iPhone. Esto funciona en todos los navegadores mientras la pestaña esté
 * abierta, que es el escenario real de alguien esperando a que le confirmen su
 * reporte.
 */
export function onReconnect(callback: () => void): () => void {
  window.addEventListener('online', callback)
  return () => window.removeEventListener('online', callback)
}
