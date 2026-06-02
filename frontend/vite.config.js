import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  build: {
    rollupOptions: {
      output: {
        // Split big third-party libs into separate, long-cacheable chunks so
        // an app code change doesn't bust the vendor cache and the browser can
        // fetch them in parallel.
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react/jsx-runtime'],
          clerk: ['@clerk/clerk-react', '@clerk/themes'],
          particles: ['@tsparticles/react', '@tsparticles/slim'],
          markdown: ['react-markdown'],
        },
      },
    },
  },
})
