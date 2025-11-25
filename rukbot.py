print("🔥 LOADED CLEAN RUKBOT.PY (STABLE VERSION)")

import os
from dotenv import load_dotenv
from openai import OpenAI

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse, PlainTextResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


# =====================================================
# 1️⃣ LOAD ENV
# =====================================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")


# =====================================================
# 2️⃣ FASTAPI SETUP
# =====================================================
app = FastAPI()

app.mount("/static", StaticFiles(directory="static"), name="static")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")


# =====================================================
# 3️⃣ OPENAI CLIENT
# =====================================================
client = OpenAI(
    api_key=OPENAI_API_KEY,
    project=OPENAI_PROJECT_ID,
)


# =====================================================
# 4️⃣ RESPONSE GENERATION (STABLE)
# =====================================================
def get_full_response(user_input: str) -> str:
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=f"""
You are RukBot — the friendly, confident, casually smart expert for RUKSAK & RUKVEST.

VOICE:
- Warm, helpful, conversational.
- Sound human, not robotic.
- Short sentences. Clear, friendly tone.

PRODUCT RULES:
- RUKVEST is fixed-weight only: 3kg, 5kg, 8kg, 11kg. Never adjustable.
- Never invent features that aren’t in the PDFs.
- If the PDFs don’t mention something, reply:
  "I can’t find this in the official product specs — the team at team@ruksak.com can help with specifics."

STYLE:
- No mention of PDFs, vector stores, or internal logic.
- Just answer naturally.

USER QUESTION: {user_input}
            """,
            temperature=0.4,
        )

        # Only return plain text — nothing else.
        answer = getattr(response, "output_text", "").strip()
        if answer:
            return answer

        return "🧠 Hmm, I didn’t quite catch that — try asking in a slightly different way?"

    except Exception as e:
        print("❌ OpenAI error:", e)
        return "⚠️ I’m having trouble reaching my brain (OpenAI). Try again shortly."


# =====================================================
# 5️⃣ ROUTES
# =====================================================
@app.get("/check")
def check():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return templates.TemplateResponse("chat.html", {"request": request})


@app.post("/chat")
async def chat(request: Request):
    data = await request.json()
    user_input = data.get("message", "")
    reply = get_full_response(user_input)

    # CRITICAL: Widget and main site expect PLAIN TEXT
    return PlainTextResponse(reply)


@app.get("/widget", response_class=HTMLResponse)
async def widget(request: Request):
    return templates.TemplateResponse("rukbot-widget.html", {"request": request})
