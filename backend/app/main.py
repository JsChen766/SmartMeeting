from fastapi import FastAPI
from backend.app.routers.translation_summarization import router as nlp_router


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

    # Register routers
    app.include_router(nlp_router)

    return app


app = create_app()
