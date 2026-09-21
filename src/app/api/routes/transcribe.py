"""Flujo completo de voz a accion, que es lo que consume el frontend.

Acepta el audio grabado en el navegador (multipart) o una transcripcion
escrita a mano (JSON), lo convierte en texto, reutiliza la logica de
`/instruction` para decidir la ruta y ejecuta la accion resultante.
"""

import json

from fastapi import APIRouter, HTTPException, Request, status
from pydantic import ValidationError
from starlette.datastructures import UploadFile

from src.app.schemas.voice import InstructionRequest, TranscribeFlowResponse
from src.app.services.dispatcher import execute
from src.app.services.groq_service import resolve_instruction, transcribe_audio
from src.app.utils.language import normalize_transcription_language

router = APIRouter(tags=["transcribe"])

# El frontend graba 20 segundos como mucho; el limite de Groq son 25 MB.
MAX_AUDIO_BYTES = 25 * 1024 * 1024


@router.get("/")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@router.post("/transcribe", response_model=TranscribeFlowResponse)
async def transcribe_and_run_flow(request: Request) -> TranscribeFlowResponse:
    content_type = request.headers.get("content-type", "")

    if content_type.startswith("multipart/form-data"):
        transcription = await _transcription_from_audio(request)
    else:
        transcription = await _transcription_from_json(request)

    instruction = await resolve_instruction(transcription)
    result = execute(instruction)

    return TranscribeFlowResponse(
        transcription=transcription,
        instruction=instruction,
        result=result,
    )


async def _transcription_from_audio(request: Request) -> str:
    """Lee el audio del formulario y lo manda a Whisper."""
    form = await request.form()
    try:
        upload = form.get("file")
        if not isinstance(upload, UploadFile):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Send the recorded audio in a form field named 'file'.",
            )
        language = normalize_transcription_language(form.get("language"))
        filename = upload.filename or "command.webm"
        content = await upload.read()
    finally:
        await form.close()

    if not content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The uploaded audio is empty. Record again before sending it.",
        )
    if len(content) > MAX_AUDIO_BYTES:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="The audio file is larger than the 25 MB accepted by Groq.",
        )

    return await transcribe_audio(filename, content, language)


async def _transcription_from_json(request: Request) -> str:
    """Acepta la transcripcion manual del frontend: {"transcription": "..."}."""
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Send multipart audio in 'file', or a JSON body with a 'transcription' field.",
        ) from exc

    try:
        payload = InstructionRequest.model_validate(body)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Invalid body: {exc.errors(include_url=False)}",
        ) from exc

    transcription = payload.transcription.strip()
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'transcription' cannot be empty.",
        )
    return transcription
