print("🔥 LOADED CLEAN RUKBOT.PY (Google-free)")

import os
from datetime import datetime

from dotenv import load_dotenv
from openai import OpenAI

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware


# =====================================================
# 1️⃣ LOAD ENVIRONMENT
# =====================================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")

print("🚀 Starting RukBot server...")
print(f"🧠 Project ID: {OPENAI_PROJECT_ID}")

if not OPENAI_API_KEY:
    print("❌ WARNING: OPENAI_API_KEY is missing from .env")
if not OPENAI_PROJECT_ID:
    print("❌ WARNING: OPENAI_PROJECT_ID is missing from .env")


# =====================================================
# 2️⃣ FASTAPI APP
# =====================================================
app = FastAPI()

# Serve JS/CSS from /static
app.mount("/static", StaticFiles(directory="static"), name="static")

# ✅ FIXED CORS MIDDLEWARE (Render-compatible)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

templates = Jinja2Templates(directory="templates")


# =====================================================
# 3️⃣ OPENAI CLIENT (BASE RESPONSES API)
# =====================================================
client = OpenAI(
    api_key=OPENAI_API_KEY,
    project=OPENAI_PROJECT_ID,
)

# Keeping this for when we re-enable file_search later
VECTOR_STORE_ID = "vs_6924e48702ac81918030c4ebabe8efb9"


# =====================================================
# 4️⃣ CORE RESPONSE GENERATION
# =====================================================
def get_full_response(user_input: str) -> str:
    """
    Clean single-call pipeline using the OpenAI Responses API.
    RAG/file_search will be added after production stabilises.
    """
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=(
    "You are RukBot — the friendly, confident, casually brilliant product expert "
    "for RUKSAK & RUKVEST.\n\n"

    "==============================\n"
    "🏆 BRAND VOICE\n"
    "==============================\n"
    "• Warm, upbeat, personable — like Jarvis with a touch of Ryan Reynolds.\n"
    "• Speak like a supportive expert, not a robot.\n"
    "• Short, clear, conversational sentences.\n"
    "• No corporate jargon. No filler. No over-explaining.\n\n"

    "==============================\n"
    "📘 KNOWLEDGE PRIORITY (CRITICAL)\n"
    "==============================\n"
    "Your **single source of truth** is the official RUKSAK & RUKVEST product PDFs "
    "stored in the RUKBOT vector store.\n"
    "If the PDFs contain the answer → ALWAYS use their exact info.\n"
    "If the PDFs contradict general knowledge → the PDFs win.\n"
    "If the PDFs do NOT contain the answer → say:\n"
    "'I can’t find this in the official product specs — try the team at team@ruksak.com.'\n"
    "Never make up product details.\n\n"

    "==============================\n"
    "🦾 RUKVEST RULES\n"
    "==============================\n"
    "• The RUKVEST is a fixed-weight vest.\n"
    "• It comes in 3kg, 5kg, 8kg, and 11kg options.\n"
    "• It is NOT adjustable.\n"
    "• No weights can be inserted, removed, or swapped.\n"
    "• Never imply modular plates, removable inserts, or expandable systems.\n\n"

    "==============================\n"
    "🎒 RUKSAK RULES\n"
    "==============================\n"
    "• Only answer using information explicitly present in the PDFs.\n"
    "• Never assume features found in other backpacks.\n"
    "• Keep answers feature-accurate and spec-accurate.\n\n"

    "==============================\n"
    "⚠️ HALLUCINATION PREVENTION\n"
    "==============================\n"
    "When unsure → do NOT guess.\n"
    "When information is missing → explicitly say so.\n"
    "Never create fictional specs, features, or measurements.\n\n"

    "==============================\n"
    "🗣 STYLE\n"
    "==============================\n"
    "• Friendly but precise.\n"
    "• Confident but not salesy.\n"
    "• Helpful, human, and clear.\n"
    "• NEVER mention vector stores, embeddings, PDFs, or retrieval.\n\n"

    f"User question: {user_input}"
)

        print("\n================ RAW OPENAI RESPONSE ================")
        print(response)
        print("=====================================================\n")

        answer = getattr(response, "output_text", None)

        if isinstance(answer, str) and answer.strip():
            return answer.strip()

        return (
            "🧠 I reached OpenAI but didn't get a clear answer back. "
            "Try rephrasing that for me, or give me a bit more detail."
        )

    except Exception as e:
        print(f"⚠️ Model error in get_full_response: {e!r}")
        return (
            "🧠 I'm having trouble reaching my brain right now (the OpenAI API). "
            "If this keeps happening, let the RUKSAK team know and they'll check the backend."
        )


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
    return JSONResponse({"response": reply})


@app.get("/widget", response_class=HTMLResponse)
async def widget(request: Request):
    return templates.TemplateResponse("rukbot-widget.html", {"request": request})
