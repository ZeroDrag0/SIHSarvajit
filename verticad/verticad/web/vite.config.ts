import tailwindcss from '@tailwindcss/vite'
import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), tailwindcss()],
  // In dev, /api/* is forwarded to the FastAPI backend so the app runs against live data on one origin.
  server: { proxy: { '/api': process.env.VERTICAD_API ?? 'http://127.0.0.1:8000' } },
})
