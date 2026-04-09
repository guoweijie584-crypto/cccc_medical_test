import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  base: '/medical/',
  server: {
    port: 5173,
    host: '0.0.0.0',
    proxy: {
      // CCCC Web API (daemon :8858) — must come before /api to avoid shadowing
      '/api/v1': {
        target: 'http://127.0.0.1:8858',
        changeOrigin: true,
      },
      // Medical API Server (:8001) — memory, patient, evaluation
      '/api': {
        target: 'http://127.0.0.1:8001',
        changeOrigin: true,
      },
    },
  },
});
