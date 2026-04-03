from fastapi import FastAPI


def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Meeting Assistant API",
        version="0.1.0",
        description="Minimal FastAPI skeleton for the Smart Meeting Assistant backend.",
    )

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "smart-meeting-backend",
        }

    return app


app = create_app()
