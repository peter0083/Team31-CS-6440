import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
    envPrefix: 'VITE_', // Vite will load .env and .env.ui automatically
  server: {
    allowedHosts: true,
    host: '0.0.0.0', // Allow external access from Docker
    port: 5173,
    watch: {
      usePolling: true // Enable hot-reload in Docker
    },
  },
})
