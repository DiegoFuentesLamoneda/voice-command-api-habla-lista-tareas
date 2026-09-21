import re

from fastapi import HTTPException, status

_WHISPER_LANG = re.compile(r"^[a-z]{2}(-[a-z]{2,8})?$")


def normalize_transcription_language(raw: object) -> str | None:
    """Return ISO 639-1 code for Groq/Whisper, or None for auto-detect."""
    if raw is None:
        return None
    if isinstance(raw, (bytes, bytearray)):
        try:
            raw = raw.decode("utf-8")
        except UnicodeDecodeError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Invalid 'language' encoding.",
            ) from exc
    if not isinstance(raw, str):
        return None
    code = raw.strip().lower()
    if not code:
        return None
    if not _WHISPER_LANG.fullmatch(code):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid 'language': use ISO 639-1 such as 'es', 'en', or omit for auto-detect.",
        )
    return code.split("-", 1)[0]
