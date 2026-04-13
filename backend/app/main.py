from fastapi import BackgroundTasks, FastAPI, File, Form, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv
from pathlib import Path

from backend.app.meeting_service import MeetingService

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env")


class ProcessMeetingRequest(BaseModel):
    meeting_id: str
    target_lang: str | None = None
    enable_translation: bool = False
    translation_target_lang: str | None = None
    enable_summary: bool = True


def create_app() -> FastAPI:
    app = FastAPI(
        title="Smart Meeting Assistant API",
        version="0.1.0",
        description="Minimal FastAPI skeleton for the Smart Meeting Assistant backend.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=[
            "http://localhost:5173",
            "http://127.0.0.1:5173",
        ],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health", tags=["system"])
    def health_check() -> dict[str, str]:
        return {
            "status": "ok",
            "service": "smart-meeting-backend",
        }

    service = MeetingService()

    @app.post("/meetings/upload", tags=["meetings"])
    def upload_meeting(
        file: UploadFile = File(...),
        lang_hint: str | None = Form(default=None),
        file_name: str | None = Form(default=None),
    ) -> dict:
        return service.upload_meeting(
            file,
            lang_hint=lang_hint,
            file_name=file_name,
        )

    @app.post("/meetings/process", tags=["meetings"])
    def process_meeting(
        request: ProcessMeetingRequest,
        background_tasks: BackgroundTasks,
    ) -> dict:
        response = service.start_processing(
            meeting_id=request.meeting_id,
            target_lang=request.target_lang,
            enable_translation=request.enable_translation,
            translation_target_lang=request.translation_target_lang,
            enable_summary=request.enable_summary,
        )
        if response.get("success"):
            background_tasks.add_task(
                service.process_meeting,
                meeting_id=request.meeting_id,
                target_lang=request.target_lang,
                enable_translation=request.enable_translation,
                translation_target_lang=request.translation_target_lang,
                enable_summary=request.enable_summary,
            )
        return response

    @app.get("/meetings/{meeting_id}", tags=["meetings"])
    def get_meeting(meeting_id: str) -> dict:
        return service.get_meeting(meeting_id)

    @app.get("/meetings/{meeting_id}/transcript", tags=["meetings"])
    def get_transcript(
        meeting_id: str,
        include_translation: bool = False,
        target_lang: str | None = None,
    ) -> dict:
        return service.get_transcript(
            meeting_id,
            include_translation=include_translation,
            target_lang=target_lang,
        )

    @app.get("/meetings/{meeting_id}/summary", tags=["meetings"])
    def get_summary(meeting_id: str) -> dict:
        return service.get_summary(meeting_id)

    return app


app = create_app()
