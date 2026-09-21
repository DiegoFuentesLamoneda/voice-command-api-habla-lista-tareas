"""Almacen de tareas en memoria.

La lista `tasks` vive a nivel de modulo: no hay base de datos ni ficheros, asi
que su contenido se pierde cada vez que se reinicia el servidor. Ese es el
comportamiento esperado del proyecto.

Cada tarea es un diccionario con la forma que describe `TaskDict`. Las
funciones devuelven copias para que nadie mute el almacen por accidente desde
fuera.
"""

from itertools import count
from threading import Lock
from typing import TypedDict


class TaskDict(TypedDict):
    """Forma exacta de una tarea guardada en memoria."""

    id: int
    title: str
    done: bool


tasks: list[TaskDict] = []

_id_sequence = count(1)
_lock = Lock()


def list_tasks() -> list[TaskDict]:
    """Devuelve todas las tareas en el orden en que se crearon."""
    with _lock:
        return [task.copy() for task in tasks]


def create_task(title: str, done: bool = False) -> TaskDict:
    """Anade una tarea nueva con un id incremental unico."""
    with _lock:
        task: TaskDict = {"id": next(_id_sequence), "title": title, "done": done}
        tasks.append(task)
        return task.copy()


def get_task(task_id: int) -> TaskDict | None:
    with _lock:
        task = _find(task_id)
        return task.copy() if task is not None else None


def replace_task(task_id: int, title: str, done: bool) -> TaskDict | None:
    """Sustituye title y done por completo (semantica de PUT)."""
    with _lock:
        task = _find(task_id)
        if task is None:
            return None
        task["title"] = title
        task["done"] = done
        return task.copy()


def update_task(
    task_id: int,
    title: str | None = None,
    done: bool | None = None,
) -> TaskDict | None:
    """Actualiza solo los campos recibidos (semantica de PATCH)."""
    with _lock:
        task = _find(task_id)
        if task is None:
            return None
        if title is not None:
            task["title"] = title
        if done is not None:
            task["done"] = done
        return task.copy()


def delete_task(task_id: int) -> TaskDict | None:
    """Elimina la tarea y la devuelve, o None si el id no existe."""
    with _lock:
        task = _find(task_id)
        if task is None:
            return None
        tasks.remove(task)
        return task.copy()


def reset() -> None:
    """Vacia el almacen y reinicia la secuencia de ids (util en tests)."""
    global _id_sequence
    with _lock:
        tasks.clear()
        _id_sequence = count(1)


def _find(task_id: int) -> TaskDict | None:
    """Busca una tarea por id. Debe llamarse con el lock tomado."""
    return next((task for task in tasks if task["id"] == task_id), None)
