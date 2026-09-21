from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from contextlib import asynccontextmanager
from typing import Any

from fastapi import FastAPI, HTTPException, Response, status
from fastapi.responses import JSONResponse

from .audio import AudioEncodingError, encode_mp3, encode_wav
from .config import Settings
from .engine import ChatterboxEngine, SpeechEngine
from .schemas import ResponseFormat, SpeechRequest, VoiceResponse, VoicesResponse
from .service import QueueFullError, SpeechService
from .voices import VoiceCatalog, VoiceConfigurationError, load_voice_catalog


logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
LOGGER = logging.getLogger(__name__)

EngineFactory = Callable[[Settings, VoiceCatalog], SpeechEngine]


def create_app(
    *,
    settings: Settings | None = None,
    engine_factory: EngineFactory | None = None,
) -> FastAPI:
    runtime_settings = settings or Settings()
    voices = load_voice_catalog(
        runtime_settings.voices_config,
        runtime_settings.default_voice,
    )
    factory = engine_factory or ChatterboxEngine
    engine = factory(runtime_settings, voices)
    service = SpeechService(runtime_settings, engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        try:
            await asyncio.to_thread(service.load)
        except Exception:
            # Keep the process alive so /health remains useful and /health/ready
            # exposes the startup failure to Docker/Compose.
            LOGGER.exception("Chatterbox failed to load")
        yield

    app = FastAPI(
        title="Local Chatterbox TTS",
        version="0.1.0",
        lifespan=lifespan,
    )
    app.state.settings = runtime_settings
    app.state.voices = voices
    app.state.speech_service = service

    @app.get("/health", include_in_schema=False)
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/health/ready", include_in_schema=False)
    async def readiness() -> Response:
        if service.ready:
            return JSONResponse(
                {
                    "status": "ready",
                    "variant": runtime_settings.model_variant,
                    "voices": sorted(voices.voices),
                }
            )
        return JSONResponse(
            {
                "status": "not_ready",
                "error": service.load_error or "model is still loading",
            },
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        )

    @app.get("/v1/models")
    async def list_models() -> dict[str, Any]:
        created = 0
        data = [
            {
                "id": model_name,
                "object": "model",
                "created": created,
                "owned_by": "local",
            }
            for model_name in sorted(runtime_settings.accepted_models)
        ]
        return {"object": "list", "data": data}

    @app.get("/v1/audio/voices", response_model=VoicesResponse)
    async def list_voices() -> VoicesResponse:
        return VoicesResponse(
            data=[
                VoiceResponse(id=voice.id, name=voice.name, builtin=voice.builtin)
                for voice in sorted(voices.voices.values(), key=lambda item: item.id)
            ]
        )

    @app.post("/v1/audio/speech")
    async def create_speech(request: SpeechRequest) -> Response:
        if not service.ready:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail=service.load_error or "model is not ready",
            )
        if request.model not in runtime_settings.accepted_models:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=(
                    f"unknown model '{request.model}'; accepted names: "
                    f"{', '.join(sorted(runtime_settings.accepted_models))}"
                ),
            )
        if len(request.input) > runtime_settings.max_input_chars:
            raise HTTPException(
                status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                detail=(
                    f"input is {len(request.input)} characters; maximum is "
                    f"{runtime_settings.max_input_chars}"
                ),
            )
        if request.speed != 1.0:
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                detail="speed is not supported yet; use 1.0",
            )

        try:
            selected_voice = voices.get(request.voice)
            result = await service.synthesize(request.input, selected_voice.id)
            if request.response_format == ResponseFormat.WAV:
                encoded = await asyncio.to_thread(
                    encode_wav,
                    result.samples,
                    result.sample_rate,
                )
            else:
                encoded = await asyncio.to_thread(
                    encode_mp3,
                    result.samples,
                    result.sample_rate,
                    bitrate=runtime_settings.mp3_bitrate,
                    timeout_seconds=runtime_settings.ffmpeg_timeout_seconds,
                )
        except VoiceConfigurationError as exc:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=str(exc),
            ) from exc
        except QueueFullError as exc:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=str(exc),
                headers={"Retry-After": "5"},
            ) from exc
        except AudioEncodingError as exc:
            LOGGER.exception("Audio encoding failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=str(exc),
            ) from exc
        except Exception as exc:
            LOGGER.exception("Speech synthesis failed")
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"speech synthesis failed: {type(exc).__name__}",
            ) from exc

        LOGGER.info(
            "Completed TTS request: voice=%s chunks=%d audio_seconds=%.2f elapsed_seconds=%.2f",
            request.voice,
            result.chunks,
            len(result.samples) / result.sample_rate,
            result.elapsed_seconds,
        )
        return Response(
            content=encoded.data,
            media_type=encoded.media_type,
            headers={
                "Content-Disposition": f'inline; filename="speech.{encoded.file_extension}"',
                "X-Audio-Sample-Rate": str(result.sample_rate),
                "X-TTS-Chunks": str(result.chunks),
            },
        )

    return app


app = create_app()
