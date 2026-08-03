import { fileURLToPath, URL } from 'node:url'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { VitePWA } from 'vite-plugin-pwa'

// https://vite.dev/config/
export default defineConfig({
  resolve: {
    // `@` → src. Vite resolves this at build time; jsconfig.json mirrors it so
    // the editor can follow the same paths. Both must be kept in sync.
    alias: {
      '@': fileURLToPath(new URL('./src', import.meta.url)),
    },
  },
  plugins: [
    react(),
    tailwindcss(),
    VitePWA({
      registerType: 'autoUpdate',
      injectRegister: 'auto',
      includeAssets: ['favicon.svg', 'apple-touch-icon.png'],
      manifest: {
        name: 'ACE — Academic Counseling Engine',
        short_name: 'ACE',
        description:
          'Your Penn State academic advisor — course planning, degree progress, deadlines, and personalized degree-audit analysis.',
        lang: 'en',
        theme_color: '#ffffff',
        background_color: '#fafafa',
        display: 'standalone',
        orientation: 'portrait',
        scope: '/',
        start_url: '/',
        categories: ['education', 'productivity'],
        icons: [
          { src: 'pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: 'pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: 'pwa-maskable-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        globPatterns: ['**/*.{js,css,html,svg,png,woff2}'],
        navigateFallback: '/index.html',
        cleanupOutdatedCaches: true,
      },
    }),
  ],
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
