// Puts the server-rendered page into dist/index.html, so visitors see it before
// the JavaScript loads; src/main.tsx then hydrates it. Runs after both builds.
import fs from "node:fs";
import path from "node:path";
import { fileURLToPath, pathToFileURL } from "node:url";

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), "..");
const page = path.join(root, "dist/index.html");
const { render } = await import(pathToFileURL(path.join(root, "dist-ssr/entry-server.js")).href);

const html = fs.readFileSync(page, "utf8");
const marker = '<div id="root"></div>';
if (!html.includes(marker)) throw new Error(`${marker} not found in dist/index.html`);
fs.writeFileSync(page, html.replace(marker, `<div id="root">${render()}</div>`));
fs.rmSync(path.join(root, "dist-ssr"), { recursive: true, force: true });
console.log(`prerendered dist/index.html (${Math.round(fs.statSync(page).size / 1024)} KB)`);
