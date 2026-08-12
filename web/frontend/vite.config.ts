import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'
import { resolve } from 'path'

// JenPy 前端构建配置
// dev 模式下代理 /api 到本地 FastAPI（默认 8000 端口）
// build 产物输出到 ../../jenpy/web/static，供 pip 打包后 `jenpy ui` 直接托管
export default defineConfig({
  plugins: [vue()],
  resolve: {
    alias: { '@': resolve(__dirname, 'src') },
  },
  server: {
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
      '/health': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
  build: {
    outDir: '../../jenpy/web/static',
    emptyOutDir: true,
  },
})
