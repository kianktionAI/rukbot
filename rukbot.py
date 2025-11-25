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

# =====================================================
# 2️⃣ FASTAPI APP
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
# 4️⃣ RESPONSE GENERATION
# =====================================================
def get_full_response(user_input: str) -> str:
    try:
        response = client.responses.create(
            model="gpt-4.1-mini",
            input=(
                "You are RukBot — the friendly, confident product expert "
                "for RUKSAK & RUKVEST.\n\n"

                "Use ONLY information found in the official product PDFs.\n"
                "If unsure, say: 'I can’t find this in the official product specs — "
                "try the team at team@ruksak.com.'\n\n"

                "RUKVEST RULES:\n"
                "- Fixed weight: 3kg, 5kg, 8kg, 11kg.\n"
                "- Not adjustable — no removable plates.\n\n"

                f"User question: {user_input}"
            ),
            temperature=0.4,
        )

        answer = getattr(response, "output_text", None)
        if isinstance(answer, str) and answer.strip():
            return answer.strip()

        return "🧠 I reached OpenAI but didn't get a clear answer back."

    except Exception as e:
        print(f"⚠️ Model error: {e}")
        return (
            "🧠 I'm having trouble reaching my brain right now (the OpenAI API). "
            "If this keeps happening, the RUKSAK team can check the backend."
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

    # ⭐ RETURN JSON FOR WIDGET ⭐
    return JSONResponse({"response": reply})


@app.get("/widget", response_class=HTMLResponse)
async def widget(request: Request):
    return templates.TemplateResponse("rukbot-widget.html", {"request": request})

