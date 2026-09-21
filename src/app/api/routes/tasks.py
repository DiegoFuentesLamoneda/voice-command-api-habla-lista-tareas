"""Endpoints CRUD sobre la lista de tareas en memoria."""

from typing import NoReturn

from fastapi import APIRouter, HTTPException, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate
from src.app.services import task_store

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def get_tasks() -> list[Task]:
    return [Task.model_validate(task) for task in task_store.list_tasks()]


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> Task:
    task = task_store.create_task(title=payload.title.strip(), done=payload.done)
    return Task.model_validate(task)


@router.put("/{task_id}", response_model=Task)
def replace_task(
    task_id: int,
    payload: TaskReplace,
) -> Task:
    task = task_store.replace_task(
        task_id,
        title=payload.title.strip(),
        done=payload.done,
    )
    if task is None:
        raise_task_not_found(task_id)
    return Task.model_validate(task)


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    payload: TaskUpdate,
) -> Task:
    if payload.title is None and payload.done is None:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Send at least one field to update: 'title' or 'done'.",
        )

    task = task_store.update_task(
        task_id,
        title=payload.title.strip() if payload.title is not None else None,
        done=payload.done,
    )
    if task is None:
        raise_task_not_found(task_id)
    return Task.model_validate(task)


@router.delete("/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    task = task_store.delete_task(task_id)
    if task is None:
        raise_task_not_found(task_id)
    return {"message": f"Task {task_id} deleted.", "title": task["title"]}


def raise_task_not_found(task_id: int) -> NoReturn:
    """NoReturn le dice al verificador de tipos que esta funcion nunca vuelve,
    asi sabe que despues de llamarla la tarea ya no puede ser None."""
    raise HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=f"Task {task_id} not found.",
    )
