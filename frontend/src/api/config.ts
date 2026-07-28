const configuredApiUrl =
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000";
const isVercelDeployment =
  typeof window !== "undefined" && window.location.hostname.endsWith(".vercel.app");

// Vercel previews have ephemeral origins that are intentionally absent from the
// production API's exact CORS allowlist. The same-origin rewrite keeps previews
// on the configured production-safe backend without weakening backend CORS.
export const API_URL = (
  isVercelDeployment ? "/api" : configuredApiUrl
).replace(/\/$/, "");

export async function apiError(response: Response, fallback: string): Promise<Error> {
  try {
    const body = (await response.json()) as { detail?: string };
    if (typeof body.detail === "string") return new Error(body.detail);
  } catch {
    // Use the safe caller-provided fallback for non-JSON upstream failures.
  }
  return new Error(fallback);
}
