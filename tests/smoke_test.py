"""Pruebas de humo de la API, sin tocar la red.

Cubren el CRUD en memoria, el despachador de instrucciones, la validacion de la
respuesta del LLM, el flujo de /transcribe (con el modelo simulado) y CORS.
No hacen falta credenciales de Groq.

Uso, desde la raiz del repositorio:

    python -m tests.smoke_test
"""

from fastapi.testclient import TestClient

from src.app.main import app
from src.app.api.routes import transcribe as transcribe_route
from src.app.schemas.voice import InstructionPayload
from src.app.services import dispatcher, task_store
from src.app.services.groq_service import _parse_instruction

client = TestClient(app)
results = []


def check(label, ok, extra=""):
    results.append((label, ok, extra))
    status = "PASS" if ok else "FAIL"
    detail = "" if ok else "  -> " + str(extra)
    print(status + "  " + label + detail)


task_store.reset()

# ---------- CRUD ----------
r = client.get("/tasks")
check("GET /tasks vacio -> 200 []", r.status_code == 200 and r.json() == [], r.text)

r = client.post("/tasks", json={"title": "Comprar leche"})
check("POST /tasks -> 201 id=1", r.status_code == 201 and r.json() == {"id": 1, "title": "Comprar leche", "done": False}, r.text)

r = client.post("/tasks", json={"title": "Sacar la basura", "done": True})
check("POST /tasks con done -> 201 id=2", r.status_code == 201 and r.json() == {"id": 2, "title": "Sacar la basura", "done": True}, r.text)

r = client.post("/tasks", json={"done": True})
check("POST /tasks sin title -> 422", r.status_code == 422, r.status_code)

r = client.get("/tasks")
check("GET /tasks -> 2 tareas", r.status_code == 200 and len(r.json()) == 2, r.text)

r = client.put("/tasks/1", json={"title": "Comprar leche y pan", "done": True})
check("PUT /tasks/1 -> reemplazo completo", r.status_code == 200 and r.json() == {"id": 1, "title": "Comprar leche y pan", "done": True}, r.text)

r = client.put("/tasks/1", json={"title": "Solo titulo"})
check("PUT sin done -> 422", r.status_code == 422, r.status_code)

r = client.patch("/tasks/2", json={"done": False})
check("PATCH /tasks/2 done -> parcial", r.status_code == 200 and r.json() == {"id": 2, "title": "Sacar la basura", "done": False}, r.text)

r = client.patch("/tasks/2", json={"title": "Bajar la basura"})
check("PATCH /tasks/2 title -> conserva done", r.status_code == 200 and r.json() == {"id": 2, "title": "Bajar la basura", "done": False}, r.text)

r = client.patch("/tasks/2", json={})
check("PATCH vacio -> 400", r.status_code == 400, r.status_code)

r = client.patch("/tasks/99", json={"done": True})
check("PATCH inexistente -> 404", r.status_code == 404, r.status_code)

r = client.put("/tasks/99", json={"title": "x", "done": True})
check("PUT inexistente -> 404", r.status_code == 404, r.status_code)

r = client.delete("/tasks/99")
check("DELETE inexistente -> 404", r.status_code == 404, r.status_code)

r = client.delete("/tasks/1")
check("DELETE /tasks/1 -> mensaje de confirmacion", r.status_code == 200 and "message" in r.json(), r.text)

r = client.get("/tasks")
check("GET tras DELETE -> queda 1", r.status_code == 200 and [t["id"] for t in r.json()] == [2], r.text)

r = client.post("/tasks", json={"title": "Tarea nueva"})
check("ids no se reciclan tras DELETE -> id=3", r.json().get("id") == 3, r.text)

# ---------- Despachador ----------
task_store.reset()

out = dispatcher.execute(InstructionPayload(endpoint="/tasks", method="POST", params={"title": "Comprar leche"}))
check("dispatch POST /tasks", out == {"id": 1, "title": "Comprar leche", "done": False}, out)

out = dispatcher.execute(InstructionPayload(endpoint="/tasks", method="GET", params={}))
check("dispatch GET /tasks", out == [{"id": 1, "title": "Comprar leche", "done": False}], out)

out = dispatcher.execute(InstructionPayload(endpoint="/tasks/1", method="PATCH", params={"done": True}))
check("dispatch PATCH /tasks/1", out == {"id": 1, "title": "Comprar leche", "done": True}, out)

out = dispatcher.execute(InstructionPayload(endpoint="/tasks/1", method="PUT", params={"title": "Otra cosa"}))
check("dispatch PUT sin done -> done=False", out == {"id": 1, "title": "Otra cosa", "done": False}, out)

out = dispatcher.execute(InstructionPayload(endpoint="/tasks", method="PATCH", params={"task_id": "1", "done": "true"}))
check("dispatch id en params + done string", out == {"id": 1, "title": "Otra cosa", "done": True}, out)

out = dispatcher.execute(InstructionPayload(endpoint="/tasks", method="POST", params={"task": "Sinonimo de title"}))
check("dispatch alias de title", out.get("title") == "Sinonimo de title", out)

out = dispatcher.execute(InstructionPayload(endpoint="/tasks/1", method="DELETE", params={}))
check("dispatch DELETE /tasks/1", "message" in out, out)

bad_instructions = [
    ("endpoint desconocido -> 400", InstructionPayload(endpoint="/otra-cosa", method="GET", params={}), 400),
    ("DELETE sobre la coleccion, sin id -> 400", InstructionPayload(endpoint="/tasks", method="DELETE", params={}), 400),
    ("id ausente -> 400", InstructionPayload(endpoint="/tasks/{task_id}", method="PATCH", params={"done": True}), 400),
    ("tarea inexistente -> 404", InstructionPayload(endpoint="/tasks/42", method="DELETE", params={}), 404),
    ("POST sin title -> 422", InstructionPayload(endpoint="/tasks", method="POST", params={}), 422),
]
for label, payload, expected in bad_instructions:
    try:
        dispatcher.execute(payload)
        check("dispatch " + label, False, "no lanzo excepcion")
    except Exception as exc:
        check("dispatch " + label, getattr(exc, "status_code", None) == expected, type(exc).__name__ + ": " + str(exc))

# ---------- Parser de la respuesta del LLM ----------
ok = _parse_instruction('{"endpoint": "/tasks", "method": "post", "params": {"title": "Leche"}}')
check("parse: normaliza el metodo a mayusculas", ok.method == "POST" and ok.endpoint == "/tasks", ok)

ok = _parse_instruction('{"endpoint": "/tasks/2", "method": "PATCH", "body": {"done": true}}')
check("parse: acepta 'body' como params", ok.params == {"done": True}, ok)

bad_payloads = [
    ("texto libre", "claro, aqui tienes"),
    ("json que no es objeto", "[1, 2, 3]"),
    ("metodo invalido", '{"endpoint": "/tasks", "method": "FETCH", "params": {}}'),
    ("sin endpoint", '{"method": "GET", "params": {}}'),
]
for label, raw in bad_payloads:
    try:
        _parse_instruction(raw)
        check("parse rechaza " + label, False, "no lanzo excepcion")
    except Exception as exc:
        check("parse rechaza " + label, getattr(exc, "status_code", None) == 502, type(exc).__name__ + ": " + str(exc))

# ---------- Flujo /transcribe con el LLM simulado ----------
task_store.reset()
real_resolver = transcribe_route.resolve_instruction


async def fake_resolver(transcription):
    return InstructionPayload(endpoint="/tasks", method="POST", params={"title": "Comprar leche"})


transcribe_route.resolve_instruction = fake_resolver
try:
    r = client.post("/transcribe", json={"transcription": "anade comprar leche a mi lista"})
    body = r.json()
    check(
        "POST /transcribe (JSON manual) -> transcription+instruction+result",
        r.status_code == 200
        and body["transcription"] == "anade comprar leche a mi lista"
        and body["instruction"] == {"endpoint": "/tasks", "method": "POST", "params": {"title": "Comprar leche"}}
        and body["result"] == {"id": 1, "title": "Comprar leche", "done": False},
        r.text,
    )
    check(
        "la tarea quedo guardada en memoria",
        task_store.list_tasks() == [{"id": 1, "title": "Comprar leche", "done": False}],
        task_store.list_tasks(),
    )

    r = client.post("/transcribe", json={"transcription": "   "})
    check("POST /transcribe vacio -> 4xx", r.status_code in (400, 422), r.status_code)

    r = client.post("/transcribe", content=b"no soy json", headers={"Content-Type": "application/json"})
    check("POST /transcribe cuerpo invalido -> 400", r.status_code == 400, r.status_code)

    r = client.post("/transcribe", files={"nofile": ("x.txt", b"abc")})
    check("POST /transcribe multipart sin 'file' -> 400", r.status_code == 400, r.status_code)
finally:
    transcribe_route.resolve_instruction = real_resolver

# ---------- Salud y CORS ----------
r = client.get("/")
check("GET / -> healthcheck", r.status_code == 200 and r.json() == {"status": "ok"}, r.text)

r = client.options("/tasks", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST"})
check("CORS preflight desde localhost:5173", r.status_code == 200 and r.headers.get("access-control-allow-origin") == "http://localhost:5173", dict(r.headers))

r = client.options("/transcribe", headers={"Origin": "https://algo-5173.app.github.dev", "Access-Control-Request-Method": "POST"})
check("CORS preflight desde Codespaces", r.status_code == 200 and "access-control-allow-origin" in r.headers, dict(r.headers))

r = client.get("/tasks", headers={"Origin": "https://sitio-no-permitido.com"})
check("CORS bloquea un origen ajeno", "access-control-allow-origin" not in r.headers, dict(r.headers))

failed = [label for label, ok, _ in results if not ok]
print("")
print(str(len(results) - len(failed)) + "/" + str(len(results)) + " comprobaciones OK")
if failed:
    print("FALLOS: " + str(failed))
    raise SystemExit(1)
