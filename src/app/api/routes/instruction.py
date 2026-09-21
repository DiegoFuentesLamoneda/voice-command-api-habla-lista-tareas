"""Punto de entrada de enrutado: texto hablado -> JSON de enrutado."""

from fastapi import APIRouter, HTTPException, status

from src.app.schemas.voice import InstructionPayload, InstructionRequest
from src.app.services.groq_service import resolve_instruction

router = APIRouter(tags=["instruction"])


@router.post("/instruction", response_model=InstructionPayload)
async def route_instruction(
    payload: InstructionRequest,
) -> InstructionPayload:
    """Devuelve solo el endpoint, el metodo y los params: no ejecuta la accion."""
    transcription = payload.transcription.strip()
    if not transcription:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="'transcription' cannot be empty.",
        )
    return await resolve_instruction(transcription)
