# Voice Command API en 4Geeks Academy

<!-- hide -->

Por [@ehiber](https://github.com/ehiber) y [otros contribuidores](https://github.com/4GeeksAcademy/voice-command-api/graphs/contributors) en [4Geeks Academy](https://4geeksacademy.com/)

[![build by developers](https://img.shields.io/badge/build_by-Developers-blue)](https://4geeks.com)
[![4Geeks Academy](https://img.shields.io/twitter/follow/4geeksacademy?style=social&logo=x)](https://x.com/4geeksacademy)

_These instructions are also available in [English](./README.md)._

**Antes de empezar**: Lee la guia de [como comenzar un proyecto de programacion](https://4geeks.com/lesson/how-to-start-a-project) antes de escribir codigo.

> ¡Te necesitamos! Estos ejercicios se construyen y mantienen en colaboracion con personas como tu. Si encuentras algun error 🐞 o falta de ortografia, por favor contribuye y/o reportalo.

<!-- endhide -->

---

## 🎯 Tu reto

Este repositorio es el template inicial del proyecto **Voice Command API**.

El frontend ya esta construido. Graba hasta **20 segundos** de audio en el navegador, envia ese audio a tu backend y muestra:

- la transcripcion devuelta por la API
- la respuesta final de tareas devuelta por la API

Tu trabajo es implementar el backend para que todo el flujo de voz a accion funcione de punta a punta.

---

## Como funciona el proyecto

El frontend usa un unico punto de entrada publico:

- `POST /transcribe`

El frontend **no** decide intenciones con Web Speech API. Solo captura audio (hasta 20 segundos), envia el archivo a `POST /transcribe` y muestra la transcripcion devuelta por el backend para depurar mejor.

Ese endpoint debe:

1. recibir el audio grabado desde el frontend
2. transcribirlo a texto
3. reutilizar la misma logica de routing que `POST /instruction`
4. ejecutar la accion correspondiente sobre las tareas en memoria
5. devolver la transcripcion, la instruccion y el resultado final

Tu backend tambien debe exponer:

- `POST /instruction`
- `GET /tasks`
- `POST /tasks`
- `PUT /tasks/{task_id}`
- `PATCH /tasks/{task_id}`
- `DELETE /tasks/{task_id}`

Importante:

- Usa **solo almacenamiento en memoria**. No base de datos ni archivos.
- El frontend ya viene dado y no deberias modificarlo como parte del ejercicio.
- El backend incluido en este repositorio es solo un template. Tu debes completar la logica faltante.

---

## Estructura del repositorio

```text
voice-command-api/
|-- .devcontainer/           # Configuracion para Codespaces
|-- frontend/                # Frontend ya listo
|   |-- public/
|   `-- src/
|-- src/
|   `-- app/
|       |-- api/routes/      # /transcribe, /instruction, /tasks
|       |-- core/            # Configuracion
|       |-- schemas/         # Contratos de request y response
|       |-- services/        # Aqui va tu implementacion
|       `-- utils/
|-- pyproject.toml
|-- README.md
`-- README.es.md
```

---

## 🌱 Como iniciar el proyecto

Puedes abrir este proyecto en [GitHub Codespaces](https://codespaces.new/4GeeksAcademy/voice-command-api) o clonarlo localmente.

Si usas Codespaces, el repositorio ya incluye un `.devcontainer` preparado para Python, Node, FastAPI y Vite.

### Opcion A: GitHub Codespaces

1. Abre el repositorio en Codespaces.
2. Espera a que el dev container termine de instalar dependencias.
3. Crea `.env` a partir de `.env.example`.
4. Crea `frontend/.env` a partir de `frontend/.env.example`.
5. Ejecuta el backend y el frontend desde la terminal.

### Opcion B: Configuracion local

```bash
git clone https://github.com/4GeeksAcademy/voice-command-api
cd voice-command-api
```

Crea tu propio repositorio y actualiza el remoto:

```bash
git remote set-url origin https://github.com/TU_USUARIO/TU_REPOSITORIO
```

### Configuracion del backend

Crea un archivo `.env` a partir de `.env.example` y agrega tus credenciales de Groq.

Instala dependencias y ejecuta la API:

```bash
uv sync
uv run uvicorn src.main:app --reload
```

### Configuracion del frontend

Crea `frontend/.env` a partir de `frontend/.env.example`.

Ejecuta el frontend:

```bash
cd frontend
npm install
npm run dev
```

---

## 💻 Qué debes hacer

- [ ] Crea una lista `tasks` a nivel de modulo con `id`, `title` y `done`, usando IDs unicos e incrementales.
- [ ] Implementa `GET /tasks`, `POST /tasks`, `PUT /tasks/{task_id}`, `PATCH /tasks/{task_id}` y `DELETE /tasks/{task_id}` con almacenamiento en memoria.
- [ ] Implementa `POST /instruction` para recibir `{ "transcription": "..." }`, llamar a Groq y devolver **solo** JSON de routing (sin ejecutar tareas):

```json
{
  "endpoint": "/tasks",
  "method": "POST",
  "params": { "title": "Buy groceries" }
}
```

- [ ] Implementa `POST /transcribe` para aceptar `multipart/form-data`, convertir audio a texto, reutilizar la logica de `/instruction`, ejecutar la accion y devolver `transcription`, `instruction` y `result`.
- [ ] No hardcodees el routing con reglas manuales como `if "add" in text`.

⚠️ **IMPORTANTE:** El frontend no decide intenciones con Web Speech API. Solo captura audio (hasta 20 segundos), envia a `POST /transcribe` y muestra la transcripcion del backend para depurar STT vs. routing.

```json
{
  "transcription": "add buy groceries to my list",
  "instruction": {
    "endpoint": "/tasks",
    "method": "POST",
    "params": {
      "title": "Buy groceries"
    }
  },
  "result": {
    "id": 1,
    "title": "Buy groceries",
    "done": false
  }
}
```

---

## Tip para depurar

Si la transcripcion que se ve en el frontend ya esta mal, el problema esta en la captura de audio o en el speech-to-text.

Si la transcripcion esta bien pero la accion sale mal, el problema esta en `/instruction`.

---

## ✅ Qué vamos a evaluar

- [ ] `POST /transcribe` recibe audio, transcribe y reutiliza la logica de `/instruction`.
- [ ] `POST /instruction` recibe texto plano y devuelve solo JSON de routing (sin ejecutar acciones).
- [ ] `GET /tasks`, `POST /tasks`, `PUT /tasks/{task_id}`, `PATCH /tasks/{task_id}` y `DELETE /tasks/{task_id}` funcionan correctamente con memoria en proceso.
- [ ] El frontend muestra la transcripcion devuelta por el backend para distinguir errores de STT vs. errores de routing.

---

## 📦 Cómo entregar este proyecto

1. Sube tu solucion a tu repositorio de GitHub.
2. Asegurate de incluir backend y frontend configurados para correr localmente.
3. Comparte el enlace del repositorio y un breve video o GIF mostrando:
   - grabacion de audio (20 segundos maximo),
   - transcripcion visible en frontend,
   - ejecucion correcta de acciones sobre tareas.

---

Este y muchos otros proyectos son construidos por estudiantes como parte de los [Coding Bootcamps](https://4geeksacademy.com/) de 4Geeks Academy. Encuentra mas acerca de los cursos de [Full-Stack Software Developer](https://4geeksacademy.com/es/programas-de-carrera/desarrollo-full-stack), [Data Science & Machine Learning](https://4geeksacademy.com/en/career-programs/data-science-ml), [Ciberseguridad](https://4geeksacademy.com/es/programas-de-carrera/ciberseguridad) e [Ingeniería de IA](https://4geeksacademy.com/es/programas-de-carrera/ingenieria-ia).
