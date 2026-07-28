const configuredApiUrl = import.meta.env.VITE_API_URL?.trim();
const isVercelDeployment =
  typeof window !== "undefined" && window.location.hostname.endsWith(".vercel.app");

// An explicit environment always wins, allowing branch previews to use an
// isolated backend. Vercel falls back to the same-origin rewrite only when no
// backend is configured; local development continues to use local FastAPI.
export const API_URL = (
  configuredApiUrl || (isVercelDeployment ? "/api" : "http://127.0.0.1:8000")
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
