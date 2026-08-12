import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8000',
        changeOrigin: true,
      },
    },
  },
  // Web deployments need root-relative assets so nested SPA routes such as
  // /batch-tasks/:id can load the bundle after a direct navigation. The
  // Electron packaging script overrides this with --base ./ for file:// URLs.
  base: '/',
  build: {
    outDir: 'dist',
    emptyOutDir: true,
  },
})
