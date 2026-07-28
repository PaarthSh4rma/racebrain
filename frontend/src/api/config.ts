export const API_URL = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
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
