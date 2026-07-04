import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Dev proxy: the client uses a relative "/api" base, so the browser stays same-origin and the
    // Vite dev server forwards /api to the FastAPI backend — no CORS, no hardcoded host in the app.
    proxy: {
      "/api": { target: "http://localhost:8000", changeOrigin: true },
    },
  },
});
