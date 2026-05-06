# Oráculo Digital Era de Acuario — Backend API

Motor de inteligencia artificial del Oráculo. 12 arquetipos. Una presencia.

## Stack

- **FastAPI** (Python 3.12) — API REST
- **Anthropic Claude** — Generación de lecturas
- **Supabase** — Base de datos PostgreSQL
- **ManyChat** — Integración Instagram DM

---

## Setup rápido

### 1. Clonar y configurar entorno

```bash
python -m venv venv
source venv/bin/activate   # Mac/Linux
# venv\Scripts\activate   # Windows

pip install -r requirements.txt
```

### 2. Configurar variables de entorno

```bash
cp .env.example .env
# Editar .env con tus credenciales reales
```

Variables obligatorias:
- `ANTHROPIC_API_KEY` — Tu clave de Anthropic
- `SUPABASE_URL` y `SUPABASE_SERVICE_ROLE_KEY` — Tu proyecto Supabase

### 3. Crear schema en Supabase

Ir a Supabase → SQL Editor → pegar contenido de `supabase/schema.sql` → Run.

### 4. Correr el servidor

```bash
uvicorn app.main:app --reload
```

API disponible en: http://localhost:8000
Documentación interactiva: http://localhost:8000/docs

---

## Endpoints principales

### `POST /api/oracle/reading`

Genera una lectura del Oráculo.

```json
{
  "user_id": "uuid",
  "user_name": "Ana",
  "input_text": "No sé si debo quedarme o irme, y eso me paraliza",
  "reading_type": "free"
}
```

Respuesta:
```json
{
  "session_id": "uuid",
  "archetype": { "id": "EL_UMBRAL", "name": "El Umbral", "symbol": "⬡", ... },
  "reading": "Texto de la lectura...",
  "question_for_user": "¿Qué estás protegiendo al no decidir?",
  "cta": "El Umbral tiene más profundidad...",
  "confidence": 0.455
}
```

### `POST /api/oracle/classify`

Clasifica un input sin generar lectura (debug).

```json
{ "input": "No puedo soltar esto" }
```

### `POST /api/webhook/manychat`

Webhook para ManyChat. Recibe el mensaje de Instagram DM y retorna la lectura en formato ManyChat Dynamic Content v2.

### `GET /health`

Estado del servidor.

---

## Deploy en Railway

```bash
# Instalar Railway CLI
npm install -g @railway/cli

# Login y deploy
railway login
railway init
railway up
```

Configurar variables de entorno en Railway Dashboard → Variables.

## Deploy en Render

1. Crear nuevo Web Service en render.com
2. Conectar repositorio GitHub
3. Build command: `pip install -r requirements.txt`
4. Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
5. Agregar variables de entorno en el panel

---

## Estructura del proyecto

```
oraculo-era-acuario/
├── app/
│   ├── main.py              # FastAPI app y middleware
│   ├── config.py            # Settings y variables de entorno
│   ├── models.py            # Modelos Pydantic (request/response)
│   ├── archetypes.py        # Los 12 arquetipos con system_prompts
│   ├── archetype_engine.py  # Motor de clasificación por keywords
│   ├── routers/
│   │   ├── oracle.py        # Endpoints /api/oracle/*
│   │   └── webhook.py       # Endpoint /api/webhook/manychat
│   └── services/
│       └── claude_service.py # Integración Anthropic API
├── supabase/
│   └── schema.sql           # Schema completo de la base de datos
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── .env.example
```

---

## Criterio de éxito (Sprint 1)

Input: `"No sé si debo quedarme o irme, y eso me paraliza"`

✅ Sistema asigna **EL_UMBRAL** con confianza > 0.4  
✅ Genera lectura de 200–280 palabras en voz del Oráculo  
✅ Incluye pregunta final  
⏳ Responde en < 3 segundos (requiere API key real para medir)  
⏳ Almacena en Supabase (requiere credenciales)
