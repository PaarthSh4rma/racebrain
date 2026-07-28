import os


DEFAULT_CORS_ORIGINS = (
    "http://localhost:5173",
    "http://127.0.0.1:5173",
)


def get_cors_allowed_origins() -> list[str]:
    configured = os.getenv("CORS_ALLOWED_ORIGINS")
    if not configured:
        return list(DEFAULT_CORS_ORIGINS)

    origins = [origin.strip().rstrip("/") for origin in configured.split(",") if origin.strip()]
    if "*" in origins:
        raise ValueError(
            "CORS_ALLOWED_ORIGINS must contain explicit origins when credentials are enabled."
        )
    return origins
