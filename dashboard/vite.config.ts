import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { squadWatcherPlugin } from "./src/plugin/squadWatcher";

export default defineConfig({
  plugins: [react(), squadWatcherPlugin()],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    proxy: {
      // Backend NEMO (FastAPI) — python nemo_server.py
      "/api/nemo": {
        target: "http://127.0.0.1:8798",
        changeOrigin: true,
      },
    },
  },
});
