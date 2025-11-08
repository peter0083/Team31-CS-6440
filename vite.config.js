import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    host: '0.0.0.0',  // Allow external access from Docker
    port: 5173,
    watch: {
      usePolling: true  // Enable hot-reload in Docker
    },
    allowedHosts: 'all'  // Allow all hosts (or use wildcard pattern)
  }
})
