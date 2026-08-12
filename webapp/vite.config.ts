import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Собирается на этапе Docker-сборки (Node-стадия) и раздаётся как статика
// тем же aiohttp-сервером, что и /api/* — см. app/webapp/server.py.
export default defineConfig({
  plugins: [react()],
  base: "/",
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
  },
});
