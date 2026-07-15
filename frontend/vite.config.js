import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://start-camp-16-6.onrender.com/',
        changeOrigin: true
      }
    }
  }
})