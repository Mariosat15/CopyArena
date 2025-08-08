import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      "@": "/src",
    },
  },
  preview: {
    port: 3000,
    host: '0.0.0.0',
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      'copyarena.onrender.com',
      '.onrender.com'
    ]
  },
  server: {
    port: 3000,
    host: '0.0.0.0',
    allowedHosts: [
      'localhost',
      '127.0.0.1',
      '0.0.0.0',
      'copyarena.onrender.com',
      '.onrender.com' // Allow all Render subdomains
    ],
                proxy: {
              '/api': {
                target: 'http://127.0.0.1:8002',
                changeOrigin: true,
              },
              '/ws': {
                target: 'ws://127.0.0.1:8002',
                ws: true,
                changeOrigin: true,
              }
            }
  }
}) 