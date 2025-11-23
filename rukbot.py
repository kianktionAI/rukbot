import os
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

# =====================================================
# 1️⃣ ENVIRONMENT SETUP
# =====================================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")

print("🚀 Starting RukBot server...")
print(f"🧠 Project ID: {OPENAI_PROJECT_ID}")

# =====================================================
# 2️⃣ FASTAPI APP CONFIGURATION
# =====================================================
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# =====================================================
# 3️⃣ OPENAI CLIENT SETUP
# =====================================================
client = OpenAI(
    api_key=OPENAI_API_KEY,
    project=OPENAI_PROJECT_ID
)

# =====================================================
# 4️⃣ VECTOR STORE SETUP (OpenAI RAG)
# =====================================================
VECTOR_STORE_ID = "vs_692376ab13b48191a0c2db14283160e9"

response_count = 0  # tracks first vs follow-up

# =====================================================
# 5️⃣ GOOGLE SHEET LOGGING
# =====================================================
def log_to_google_sheet(question, response):
    try:
        creds_path = (
            "/etc/secrets/service_account.json"
            if os.getenv("RENDER")
            else "service_account_rukbot.json"
        )

        creds = Credentials.from_service_account_file(
            creds_path,
            scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        sheet = gspread.authorize(creds).open("RukBot Logs")
        worksheet = sheet.worksheet("Sheet1")

        worksheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            question,
            response
        ])

    except Exception as e:
        print(f"⚠️ Logging to Google Sheet failed: {e}")

# =====================================================
# 6️⃣ RUKBOT RESPONSE GENERATION (WITH VECTOR STORE RAG)
# =====================================================
def get_full_response(user_input):
    try:
        # 🧠 OpenAI Retrieval-enhanced Response
        response = client.responses.create(
            model="gpt-4.1-mini",

            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are RukBot — a casually brilliant AI for RUKVEST & RUKSAK. "
                        "Be concise, confident, and human. No greetings. "
                        "Only use emojis sparingly for clarity. "
                        "Never reference documents, PDFs, or retrieval instructions."
                    )
                },
                {
                    "role": "user",
                    "content": user_input
                }
            ],

            tools=[{
                "type": "file_search",
                "file_search": {
                    "vector_store_ids": [VECTOR_STORE_ID]
                }
            }],

            temperature=0.7
        )

        # Extract the assistant text output
        answer = response.output_text

        if not answer:
            return (
                "🧠 Great question! Let me check on that for you. "
                "You can also email team@ruksak.com — they’ve got your back!"
            )

        return answer.strip()

    except Exception as e:
        print(f"⚠️ Retrieval or model request failed: {e}")
        return (
            "🧠 Great question! Let me check on that for you. "
            "You can email team@ruksak.com — they’ve got your back!"
        )

# =====================================================
# 🔟 FASTAPI ROUTES
# =====================================================
@app.get("/check")
async def check():
    return {"status": "ok"}

@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request):
    global response_count
    response_count = 0
    return templates.TemplateResponse("chat.html", {"request": request})

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_input = data.get("message", "")

    full_response = get_full_response(user_input)

    log_to_google_sheet(user_input, full_response)

    return JSONResponse({"response": full_response})

@app.get("/widget", response_class=HTMLResponse)
async def get_widget(request: Request):
    global response_count
    response_count = 0
    return templates.TemplateResponse("rukbot-widget.html", {"request": request})
