import { cp, mkdir, rm, writeFile } from "node:fs/promises";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const source = resolve(root, "static");
const output = resolve(root, "dist");

const config = {
  API_BASE_URL: process.env.VITE_API_BASE_URL || "",
  SUPABASE_URL: process.env.VITE_SUPABASE_URL || "",
  SUPABASE_ANON_KEY: process.env.VITE_SUPABASE_ANON_KEY || "",
  AUTH_MODE: process.env.VITE_AUTH_MODE || "authenticated",
};

await rm(output, { recursive: true, force: true });
await mkdir(output, { recursive: true });
await cp(source, output, { recursive: true });
await writeFile(
  resolve(output, "config.js"),
  `window.SES_CONFIG = ${JSON.stringify(config, null, 2)};\n`,
  "utf8",
);
