/// <reference types="vite/client" />

/** Variables de entorno del frontend. `VITE_API_BASE_URL` apunta al gateway. */
interface ImportMetaEnv {
  readonly VITE_API_BASE_URL?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
