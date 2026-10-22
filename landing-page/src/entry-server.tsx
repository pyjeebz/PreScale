import { StrictMode } from "react";
import { renderToString } from "react-dom/server";
import App from "./App.tsx";

/** Renders the page to HTML at build time (scripts/prerender.mjs), so it paints before any JavaScript runs. */
export function render() {
  return renderToString(
    <StrictMode>
      <App />
    </StrictMode>,
  );
}
