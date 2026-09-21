"""Ejecuta la instruccion que devolvio el LLM contra los endpoints de tareas.

El despachador no decide nada: se limita a traducir el JSON de enrutado
(endpoint + method + params) a la llamada correspondiente. Reutiliza los
handlers de `/tasks` para que la logica y los codigos de error sean los mismos
que ve el frontend cuando llama a la API por su cuenta.
"""

import re
from typing import Any, cast

from fastapi import HTTPException, status
from pydantic import BaseModel, ValidationError

from src.app.api.routes import tasks as tasks_routes
from src.app.schemas.voice import (
    InstructionPayload,
    TaskCreate,
    TaskReplace,
    TaskUpdate,
)

_ITEM_PATH = re.compile(r"^/tasks/(\d+)/?$")

# El modelo casi siempre usa "title"/"done", pero de vez en cuando elige un
# sinonimo o deja el id fuera del path. Normalizarlo evita perder una orden
# hablada por un detalle de formato.
_TITLE_KEYS = ("title", "task", "text", "name")
_DONE_KEYS = ("done", "completed", "complete", "is_done")
_ID_KEYS = ("task_id", "id")


def execute(instruction: InstructionPayload) -> Any:
    """Corre la accion descrita por la instruccion y devuelve su resultado."""
    endpoint = _normalize_endpoint(instruction.endpoint)
    method = instruction.method.upper()
    params = dict(instruction.params or {})
    fields = _task_fields(params)
    task_id = _find_task_id(endpoint, params)

    if method == "GET":
        # La especificacion no incluye GET /tasks/<id>: siempre se lista todo.
        return _dump(tasks_routes.get_tasks())

    if method == "POST":
        return _dump(tasks_routes.create_task(_build(TaskCreate, fields)))

    if method in {"PUT", "PATCH", "DELETE"}:
        if task_id is None:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"{method} needs a task id and the instruction has none: {instruction.endpoint!r}",
            )
        if method == "PUT":
            # PUT reemplaza la tarea entera; si falta done, queda pendiente.
            fields.setdefault("done", False)
            return _dump(tasks_routes.replace_task(task_id, _build(TaskReplace, fields)))
        if method == "PATCH":
            return _dump(tasks_routes.update_task(task_id, _build(TaskUpdate, fields)))
        return tasks_routes.delete_task(task_id)

    raise HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"Unsupported route for this API: {method} {endpoint}",
    )


def _normalize_endpoint(raw: str) -> str:
    """Deja el path en la forma /tasks o /tasks/<id>."""
    endpoint = (raw or "").split("?", 1)[0].strip()
    if not endpoint.startswith("/"):
        endpoint = f"/{endpoint}"
    if not endpoint.startswith("/tasks"):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"The model routed to an unknown endpoint: {raw!r}",
        )
    return endpoint


def _find_task_id(endpoint: str, params: dict[str, Any]) -> int | None:
    """Saca el id del path y, si el modelo lo dejo fuera, de los params."""
    match = _ITEM_PATH.fullmatch(endpoint)
    if match:
        return int(match.group(1))

    for key in _ID_KEYS:
        value = params.get(key)
        if isinstance(value, bool):
            continue
        if isinstance(value, int):
            return value
        if isinstance(value, str) and value.strip().isdigit():
            return int(value.strip())

    return None


def _task_fields(params: dict[str, Any]) -> dict[str, Any]:
    """Normaliza los params del modelo a las claves title/done."""
    fields: dict[str, Any] = {}

    for key in _TITLE_KEYS:
        value = params.get(key)
        if isinstance(value, str) and value.strip():
            fields["title"] = value.strip()
            break

    for key in _DONE_KEYS:
        value = params.get(key)
        if isinstance(value, bool):
            fields["done"] = value
            break
        if isinstance(value, str) and value.strip().lower() in {"true", "false"}:
            fields["done"] = value.strip().lower() == "true"
            break

    return fields


def _build(model: type[BaseModel], fields: dict[str, Any]) -> Any:
    try:
        return model(**fields)
    except ValidationError as exc:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"The instruction is missing valid params for this action: {exc.errors(include_url=False)}",
        ) from exc


def _dump(result: Any) -> Any:
    """Convierte los modelos Pydantic en JSON plano para el campo `result`."""
    if isinstance(result, BaseModel):
        return result.model_dump()
    if isinstance(result, list):
        return [_dump(item) for item in cast(list[Any], result)]
    return result
