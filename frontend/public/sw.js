/**
 * Service worker de la Plataforma de Emergencias (§4.4).
 *
 * Dos estrategias distintas, y la diferencia entre ellas es una decisión de
 * seguridad, no de rendimiento:
 *
 *   - App shell (HTML, JS, CSS, tiles del mapa)  → cache-first
 *     Son estáticos y versionados. Servirlos de caché hace que la aplicación
 *     abra sin conexión, que es el requisito.
 *
 *   - API (/v1/...)                              → network-first, SIN caché
 *     El estado de una emergencia cambia constantemente. Mostrar "ASSIGNED"
 *     desde la caché cuando en realidad ya está "RESOLVED" —o al revés— es peor
 *     que mostrar un error honesto: alguien podría dejar de enviar ayuda por un
 *     dato viejo. Si la red falla, se propaga el fallo y la interfaz lo muestra.
 */

const CACHE = 'emergency-shell-v1'

// Solo la raíz: los nombres de los bundles llevan hash y cambian en cada build,
// así que no se pueden listar aquí. Se cachean al vuelo en el fetch.
const APP_SHELL = ['/', '/index.html']

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE)
      .then((cache) => cache.addAll(APP_SHELL))
      // Sin esto habría que cerrar todas las pestañas para que un service
      // worker nuevo tomara el control. En una emergencia nadie hace eso.
      .then(() => self.skipWaiting()),
  )
})

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(keys.filter((key) => key !== CACHE).map((key) => caches.delete(key))),
      )
      .then(() => self.clients.claim()),
  )
})

self.addEventListener('fetch', (event) => {
  const { request } = event

  // Un POST no se cachea nunca, y menos el alta de una emergencia.
  if (request.method !== 'GET') return

  const url = new URL(request.url)

  // Llamadas a la API y a Supabase: red directa, sin tocar caché.
  const isApiCall =
    url.pathname.startsWith('/v1/') ||
    url.hostname.endsWith('.amazonaws.com') ||
    url.hostname.endsWith('.supabase.co')

  if (isApiCall) return

  // Navegaciones: se intenta la red y se cae al index cacheado. Esto es lo que
  // permite recargar en /operator o /track/:id estando sin conexión.
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request).catch(() =>
        caches.match('/index.html').then((cached) => cached ?? Response.error()),
      ),
    )
    return
  }

  // Estáticos: caché primero; si no está, red y se guarda para la próxima.
  event.respondWith(
    caches.match(request).then((cached) => {
      if (cached) return cached

      return fetch(request)
        .then((response) => {
          // Las respuestas opacas (tiles de OpenStreetMap, sin CORS) se cachean
          // igual: no se puede inspeccionar su estado, pero sirven para pintar
          // el mapa sin conexión.
          if (response.ok || response.type === 'opaque') {
            const copy = response.clone()
            caches.open(CACHE).then((cache) => cache.put(request, copy))
          }
          return response
        })
        .catch(() => cached ?? Response.error())
    }),
  )
})
