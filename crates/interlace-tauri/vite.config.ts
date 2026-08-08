import { svelte } from "@sveltejs/vite-plugin-svelte";
import tailwindcss from "@tailwindcss/vite";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig } from "vite";

const root = path.dirname(fileURLToPath(import.meta.url));

const host = process.env.TAURI_DEV_HOST;

export default defineConfig({
  plugins: [tailwindcss(), svelte()],
  resolve: {
    alias: {
      $lib: path.join(root, "web/lib"),
    },
  },
  clearScreen: false,
  server: {
    port: 1420,
    strictPort: true,
    host: host || false,
    hmr: host ? { protocol: "ws", host, port: 1421 } : undefined,
    watch: {
      ignored: ["**/src/**", "**/target/**", "**/gen/**"],
    },
  },
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
});
