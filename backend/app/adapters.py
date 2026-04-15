from __future__ import annotations

from typing import Any


API_TO_INTERNAL_LANG = {
    "man": "zh",
    "can": "yue",
    "eng": "en",
}

INTERNAL_TO_API_LANG = {
    "zh": "man",
    "yue": "can",
    "en": "eng",
}


def to_internal_lang(lang: str | None, default: str = "zh") -> str:
    if not lang:
        return default
    normalized = lang.strip().lower()
    return API_TO_INTERNAL_LANG.get(normalized, normalized)


def to_api_lang(lang: str | None, default: str = "man") -> str:
    if not lang:
        return default
    normalized = lang.strip().lower()
    return INTERNAL_TO_API_LANG.get(normalized, normalized)


def success_response(message: str, data: Any) -> dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data,
        "error": None,
    }


def error_response(
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "success": False,
        "message": "request failed",
        "data": None,
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        },
    }


def adapt_transcript_segment(
    segment: dict[str, Any],
    *,
    source_lang: str | None = None,
    target_lang: str | None = None,
    include_translation: bool = False,
) -> dict[str, Any]:
    adapted = dict(segment)
    adapted["lang"] = to_api_lang(str(adapted.get("lang", source_lang or "")))

    if "translated_text" in adapted and "translation" not in adapted:
        adapted["translation"] = adapted.pop("translated_text")

    if include_translation and adapted.get("translation") is not None:
        adapted["source_lang"] = to_api_lang(source_lang or adapted.get("lang"))
        adapted["target_lang"] = to_api_lang(target_lang)
    else:
        adapted.pop("translated_text", None)
        adapted.pop("translation", None)
        adapted.pop("source_lang", None)
        adapted.pop("target_lang", None)

    return adapted


def adapt_transcript_segments(
    segments: list[dict[str, Any]],
    *,
    source_lang: str | None = None,
    target_lang: str | None = None,
    include_translation: bool = False,
) -> list[dict[str, Any]]:
    return [
        adapt_transcript_segment(
            segment,
            source_lang=source_lang,
            target_lang=target_lang,
            include_translation=include_translation,
        )
        for segment in segments
    ]

