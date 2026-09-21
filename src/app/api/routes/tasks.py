from fastapi import APIRouter, HTTPException, status

from src.app.schemas.voice import Task, TaskCreate, TaskReplace, TaskUpdate

router = APIRouter(prefix="/tasks", tags=["tasks"])


@router.get("", response_model=list[Task])
def get_tasks() -> list[Task]:
    raise_not_implemented("GET /tasks")


@router.post("", response_model=Task, status_code=status.HTTP_201_CREATED)
def create_task(payload: TaskCreate) -> Task:
    _ = payload
    raise_not_implemented("POST /tasks")


@router.put("/{task_id}", response_model=Task)
def replace_task(
    task_id: int,
    payload: TaskReplace,
) -> Task:
    _ = (task_id, payload)
    raise_not_implemented("PUT /tasks/{task_id}")


@router.patch("/{task_id}", response_model=Task)
def update_task(
    task_id: int,
    payload: TaskUpdate,
) -> Task:
    _ = (task_id, payload)
    raise_not_implemented("PATCH /tasks/{task_id}")


@router.delete("/{task_id}")
def delete_task(task_id: int) -> dict[str, str]:
    _ = task_id
    raise_not_implemented("DELETE /tasks/{task_id}")


def raise_not_implemented(endpoint: str) -> None:
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail=f"Template endpoint pending implementation: {endpoint}",
    )
