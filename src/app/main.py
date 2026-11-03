import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.app.core.config import get_settings
from src.app.api.routes.instruction import router as instruction_router
from src.app.api.routes.tasks import router as tasks_router
from src.app.api.routes.transcribe import router as transcribe_router


def create_app() -> FastAPI:
    # Deja rastro de cada audio y de cada decision del modelo en la consola,
    # que es lo primero que se mira cuando el flujo de voz no hace lo esperado.
    # Uvicorn solo configura sus propios loggers, asi que le prestamos sus
    # manejadores para que estas lineas salgan con el mismo formato.
    logger = logging.getLogger("voice_command_api")
    logger.setLevel(logging.INFO)
    uvicorn_handlers = logging.getLogger("uvicorn.error").handlers
    if uvicorn_handlers:
        logger.handlers = uvicorn_handlers
    else:
        logging.basicConfig(level=logging.INFO)

    settings = get_settings()
    app = FastAPI(
        title="Voice Command Transcription API",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allowed_origins,
        allow_origin_regex=settings.allowed_origin_regex,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(tasks_router)
    app.include_router(instruction_router)
    app.include_router(transcribe_router)
    return app


app = create_app()
