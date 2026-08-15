import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // Fail loudly instead of drifting to 5174: a second dev server on another
    // port serves a stale app whose /api calls return index.html, which shows up
    // as "Unexpected token '<' ... is not valid JSON" in the browser.
    strictPort: true,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, ""),
      },
      "/static": "http://127.0.0.1:8000",
    },
  },
});
