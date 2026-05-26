import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import path from 'path'

const DEFAULT_DEV_HOST = '127.0.0.1'
const DEFAULT_DEV_PORT = 5180

// https://vite.dev/config/
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: {
      '@': path.resolve(__dirname, 'src'),
    }
  },
  server: {
    host: DEFAULT_DEV_HOST,
    port: DEFAULT_DEV_PORT,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api/v1')
      }
    }
  },
  build: {
    sourcemap: true,
    minify: 'esbuild',
    rollupOptions: {
      output: {
        manualChunks: {
          vue: ['vue', 'pinia'],
          markdown: ['marked', 'dompurify'],
          vendor: ['axios', '@vueuse/core', 'clsx', 'tailwind-merge'],
        }
      }
    }
  }
})
