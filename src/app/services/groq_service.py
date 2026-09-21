"""Integracion con Groq: voz a texto (Whisper) e intencion a ruta (LLM).

Aqui vive toda la "inteligencia" del backend. No hay reglas manuales del tipo
`if "anade" in texto`: la decision de que endpoint llamar la toma siempre el
modelo, y este modulo solo se encarga de pedirsela bien y de validar que la
respuesta tenga la forma esperada.
"""

import json
from functools import lru_cache
from typing import Any, cast

from fastapi import HTTPException, status
from groq import AsyncGroq, GroqError
from pydantic import ValidationError

from src.app.core.config import get_settings
from src.app.schemas.voice import InstructionPayload
from src.app.services import task_store

SYSTEM_PROMPT = """\
You are the routing layer of a voice-controlled task API. You receive one \
spoken instruction, already transcribed to text, and you translate it into a \
single HTTP call against that API.

Reply with one JSON object and nothing else, using exactly these three keys:
{"endpoint": "<path>", "method": "<HTTP method>", "params": {<arguments>}}

Available routes:
- GET /tasks -> list every task. params: {}
- POST /tasks -> create a task. params: {"title": "<text>"} (optional "done": <bool>)
- PUT /tasks/<id> -> replace a task entirely. params: {"title": "<text>", "done": <bool>}
- PATCH /tasks/<id> -> change the title and/or the done flag. params: {"title": "<text>"} and/or {"done": <bool>}
- DELETE /tasks/<id> -> remove a task. params: {}

Rules:
- <id> must be a real numeric id taken from CURRENT TASKS below, written inside \
the path, for example "/tasks/3". Never invent an id and never leave a \
placeholder in the path.
- Identify the task the user means by meaning, not by exact wording: the \
transcription may be misheard, inflected, shortened or in another language.
- "done", "finished", "completed", "ya la hice" -> PATCH with {"done": true}. \
Reopening it -> PATCH with {"done": false}.
- Renaming or correcting the wording of a task -> PATCH with {"title": "<new text>"}. \
Use PUT only when the user replaces both the title and the state at once.
- Titles keep the language the user spoke and drop filler: "add buy milk to my \
list" -> "Buy milk"; "anade comprar leche a mi lista" -> "Comprar leche".
- Deleting every task is not a single route: if the user asks for something that \
no single call can do, or the request is unclear, unrelated, or refers to a task \
that is not listed, answer {"endpoint": "/tasks", "method": "GET", "params": {}}.
- Never output explanations, markdown, code fences, or any key other than \
endpoint, method and params.

CURRENT TASKS (JSON): %s"""

_ALLOWED_METHODS = {"GET", "POST", "PUT", "PATCH", "DELETE"}


@lru_cache
def get_client() -> AsyncGroq:
    """Cliente asincrono de Groq, creado una sola vez por proceso."""
    settings = get_settings()
    return AsyncGroq(
        api_key=settings.groq_api_key,
        timeout=settings.request_timeout_seconds,
    )


async def transcribe_audio(
    filename: str,
    content: bytes,
    language: str | None = None,
) -> str:
    """Convierte el audio grabado en el navegador a texto con Whisper."""
    settings = get_settings()
    options: dict[str, Any] = {
        "file": (filename, content),
        "model": settings.groq_transcription_model,
        "temperature": 0,
    }
    if language:
        options["language"] = language

    try:
        response = await get_client().audio.transcriptions.create(**options)
    except GroqError as exc:
        raise _groq_unavailable("transcribe the audio", exc) from exc

    transcription = (getattr(response, "text", "") or "").strip()
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="No speech was detected in the audio. Record again and speak closer to the mic.",
        )
    return transcription


async def resolve_instruction(transcription: str) -> InstructionPayload:
    """Pregunta al LLM que endpoint corresponde a la instruccion hablada."""
    settings = get_settings()
    current_tasks = json.dumps(task_store.list_tasks(), ensure_ascii=False)

    try:
        completion = await get_client().chat.completions.create(
            model=settings.groq_model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT % current_tasks},
                {"role": "user", "content": transcription},
            ],
        )
    except GroqError as exc:
        raise _groq_unavailable("resolve the instruction", exc) from exc

    return _parse_instruction(completion.choices[0].message.content)


def _parse_instruction(raw: str | None) -> InstructionPayload:
    """Valida que el LLM haya devuelto el JSON de enrutado que pedimos."""
    try:
        parsed: object = json.loads(raw or "")
    except json.JSONDecodeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The model did not return valid JSON: {raw!r}",
        ) from exc

    if not isinstance(parsed, dict):
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The model returned JSON that is not an object: {raw!r}",
        )

    # json.loads no puede tipar lo que devuelve. A partir de la comprobacion de
    # arriba sabemos que es un objeto JSON, asi que lo tratamos como tal.
    data = cast(dict[str, Any], parsed)

    # El modelo a veces envuelve los argumentos con otro nombre.
    raw_params: object = data.get("params") or data.get("body") or data.get("arguments") or {}
    params = cast(dict[str, Any], raw_params) if isinstance(raw_params, dict) else {}

    try:
        instruction = InstructionPayload(
            endpoint=str(data.get("endpoint", "")).strip(),
            method=str(data.get("method", "")).strip().upper(),
            params=params,
        )
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The model returned an incomplete routing payload: {raw!r}",
        ) from exc

    if instruction.method not in _ALLOWED_METHODS:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"The model chose an unsupported method: {instruction.method!r}",
        )

    return instruction


def _groq_unavailable(action: str, exc: GroqError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_502_BAD_GATEWAY,
        detail=f"Groq could not {action}: {exc}",
    )
