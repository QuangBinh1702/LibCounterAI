import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Dev proxy target — keep localhost to match the app's configured API host.
const apiTarget = process.env.VITE_API_PROXY_TARGET || 'http://localhost:8000'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: apiTarget,
        changeOrigin: true,
      },
    },
  },
})
