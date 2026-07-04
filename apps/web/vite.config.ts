import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Uncomment once apps/api is live to proxy /api to the FastAPI backend in dev:
    // proxy: {
    //   "/api": { target: "http://localhost:8000", changeOrigin: true },
    // },
  },
});
