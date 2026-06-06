import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

const apiOrigin = process.env.VITE_DEV_API_PROXY ?? "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": apiOrigin,
      "/health": apiOrigin,
    },
  },
});
