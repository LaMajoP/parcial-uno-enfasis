import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',
    port: 3000,
    // El bind mount desde el host no siempre propaga eventos de inotify al
    // contenedor; el sondeo garantiza que el hot reload funcione en Docker.
    watch: { usePolling: true },
  },
})
