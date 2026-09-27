import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import path from "node:path";
import { squadWatcherPlugin } from "./src/plugin/squadWatcher";

export default defineConfig({
  plugins: [
    react(),
    squadWatcherPlugin(),
  ],
  resolve: {
    alias: {
      "@": path.resolve(__dirname, "./src"),
    },
  },
  server: {
    host: "127.0.0.1",
    proxy: {
      "/api/nemo": {
        target: "http://127.0.0.1:8798",
        changeOrigin: true,
      },
      "/api/auth": {
        target: "http://127.0.0.1:8798",
        changeOrigin: true,
      },
      "/api/admin": {
        target: "http://127.0.0.1:8798",
        changeOrigin: true,
      },
    },
  },
  build: {
    rollupOptions: {
      output: {
        manualChunks: {
          phaser: ["phaser"],
          zustand: ["zustand"],
        },
      },
    },
    chunkSizeWarningLimit: 2000,
  },
});