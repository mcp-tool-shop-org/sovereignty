/// <reference types="vitest" />
import react from "@vitejs/plugin-react";
import { defineConfig } from "vite";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 1420,
    strictPort: true,
  },
  clearScreen: false,
  envPrefix: ["VITE_", "TAURI_"],
  test: {
    environment: "happy-dom",
    globals: true,
    exclude: ["**/node_modules/**", "**/dist/**", "**/._*"],
  },
});
