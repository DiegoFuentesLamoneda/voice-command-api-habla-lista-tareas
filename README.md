# Voice Command API — Habla con tu lista de tareas

Backend en **FastAPI** para una interfaz de voz: el usuario habla, el audio se
transcribe con **Whisper (Groq)**, un **LLM (Groq)** decide qué endpoint de la
API hay que llamar, y la acción se ejecuta sobre una lista de tareas en memoria.

No hay reglas manuales del tipo `if "añade" in texto`: **todas** las decisiones
de enrutado salen de la respuesta del modelo.

> El enunciado original del ejercicio está en [README.es.md](README.es.md).

---

## Flujo completo

```
navegador (20 s de audio)
        │  POST /transcribe   (multipart: file + language)
        ▼
  Whisper en Groq  ─────────────▶  "añade comprar leche a mi lista"
        │
        ▼
  LLM en Groq (mismo prompt que POST /instruction)
        │
        ▼  { "endpoint": "/tasks", "method": "POST", "params": { "title": "Comprar leche" } }
  despachador ──▶ POST /tasks ──▶ lista en memoria
        │
        ▼
  { transcription, instruction, result }  ──▶  el frontend lo pinta en el chat
```

El frontend incluido usa **un único punto de entrada**, `POST /transcribe`, y
muestra siempre la transcripción: si lo que se ve escrito ya es incorrecto, el
problema está en el audio o en Whisper; si la transcripción es correcta pero la
acción no, el problema está en el enrutado del LLM.

---

## Requisitos

- Python 3.11 o superior
- Node 18 o superior (solo para el frontend)
- Una API key de Groq: https://console.groq.com/keys

---

## Puesta en marcha

### Backend

```bash
python -m venv .venv
source .venv/Scripts/activate      # Linux/macOS: source .venv/bin/activate
pip install -e .

cp .env.example .env               # y pon tu GROQ_API_KEY dentro
uvicorn src.main:app --reload
```

La API queda en `http://127.0.0.1:8000` y la documentación interactiva en
`http://127.0.0.1:8000/docs`.

### Frontend

```bash
cp frontend/.env.example frontend/.env
cd frontend
npm install
npm run dev
```

Abre `http://localhost:5173` y pulsa **Record**. El micrófono solo funciona
sobre `localhost` o HTTPS.

---

## Variables de entorno (`.env`)

| Variable | Por defecto | Para qué sirve |
| --- | --- | --- |
| `GROQ_API_KEY` | — | **Obligatoria.** Tu clave de Groq. |
| `GROQ_MODEL` | `llama-3.1-8b-instant` | Modelo que decide el enrutado. |
| `GROQ_TRANSCRIPTION_MODEL` | `whisper-large-v3-turbo` | Modelo de voz a texto. |
| `REQUEST_TIMEOUT_SECONDS` | `45` | Timeout de las llamadas a Groq. |
| `ALLOWED_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Orígenes permitidos por CORS. |
| `ALLOWED_ORIGIN_REGEX` | dominios de Codespaces y Gitpod | Patrón extra para CORS, útil cuando el puerto público cambia en cada sesión. |

`.env` está en `.gitignore`: la clave nunca se sube al repositorio.

---

## Endpoints

| Método | Ruta | Qué hace |
| --- | --- | --- |
| `GET` | `/` | Healthcheck. |
| `POST` | `/transcribe` | Flujo completo: audio (o texto) → transcripción → enrutado → acción. |
| `POST` | `/instruction` | Solo enrutado: devuelve `endpoint`, `method` y `params`. No ejecuta nada. |
| `GET` | `/tasks` | Lista todas las tareas. |
| `POST` | `/tasks` | Crea una tarea. Devuelve `201`. |
| `PUT` | `/tasks/{task_id}` | Reemplaza la tarea completa (`title` y `done`). |
| `PATCH` | `/tasks/{task_id}` | Actualiza `title` y/o `done`. |
| `DELETE` | `/tasks/{task_id}` | Elimina la tarea y devuelve un mensaje de confirmación. |

`PUT`, `PATCH` y `DELETE` devuelven `404` si el id no existe.

### Ejemplos

```bash
# Crear una tarea
curl -X POST http://127.0.0.1:8000/tasks \
  -H "Content-Type: application/json" \
  -d '{"title": "Comprar leche"}'
# {"id":1,"title":"Comprar leche","done":false}

# Marcarla como hecha
curl -X PATCH http://127.0.0.1:8000/tasks/1 \
  -H "Content-Type: application/json" \
  -d '{"done": true}'
# {"id":1,"title":"Comprar leche","done":true}

# Solo enrutado, sin ejecutar
curl -X POST http://127.0.0.1:8000/instruction \
  -H "Content-Type: application/json" \
  -d '{"transcription": "borra la tarea de comprar leche"}'
# {"endpoint":"/tasks/1","method":"DELETE","params":{}}

# Flujo completo con texto (sin micrófono)
curl -X POST http://127.0.0.1:8000/transcribe \
  -H "Content-Type: application/json" \
  -d '{"transcription": "añade sacar la basura a mi lista"}'

# Flujo completo con audio
curl -X POST http://127.0.0.1:8000/transcribe \
  -F "file=@comando.webm" \
  -F "language=es"
```

---

## Cómo se decide la ruta

`POST /instruction` manda al LLM un system prompt que:

1. describe las cinco rutas de tareas y los `params` de cada una;
2. **incluye la lista de tareas actual en JSON**, para que el modelo pueda
   traducir «marca comprar leche como hecha» al id real (`/tasks/1`);
3. obliga a responder solo con `{"endpoint", "method", "params"}`, usando
   `response_format={"type": "json_object"}` y `temperature=0`;
4. define un fallback: si la orden no está clara o la tarea no existe, el
   modelo responde `GET /tasks`, que es inofensivo.

La respuesta se valida antes de usarse: si el modelo devuelve texto libre, un
método inventado o un JSON incompleto, la API responde `502` con el detalle en
vez de ejecutar algo a ciegas.

`POST /transcribe` reutiliza exactamente esa misma función y, además, ejecuta la
acción a través del despachador.

---

## Estructura

```
src/app/
├── main.py                  # crea la app y configura CORS
├── core/config.py           # settings desde .env
├── schemas/voice.py         # contratos de entrada y salida
├── api/routes/
│   ├── tasks.py             # los cinco endpoints CRUD
│   ├── instruction.py       # texto -> JSON de enrutado
│   └── transcribe.py        # audio o texto -> transcripción + enrutado + acción
├── services/
│   ├── task_store.py        # lista en memoria a nivel de módulo
│   ├── groq_service.py      # Whisper + LLM + validación de la respuesta
│   └── dispatcher.py        # ejecuta la instrucción sobre /tasks
└── utils/language.py        # valida el idioma que llega del frontend
```

---

## Pruebas

Hay un juego de pruebas de humo que no necesita credenciales de Groq: comprueba
el CRUD en memoria, el despachador, la validacion de la respuesta del LLM (con
el modelo simulado), el flujo de `/transcribe` y la configuracion de CORS.

```bash
python -m tests.smoke_test
```

---

## Notas

- **Sin base de datos.** Las tareas viven en una lista de Python a nivel de
  módulo (`src/app/services/task_store.py`) y se pierden al reiniciar el
  servidor: es el comportamiento esperado en este proyecto.
- Los ids son incrementales y no se reutilizan, aunque se borren tareas.
- El frontend de `frontend/` viene dado y no se ha modificado.
- El audio se limita a 25 MB, que es el máximo que acepta Groq.
