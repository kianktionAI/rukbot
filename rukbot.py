# rukbot.py

import os
import fitz  # PyMuPDF
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
from drive_utils import load_google_folder_files

# =====================================================
# 1️⃣ ENVIRONMENT SETUP
# =====================================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "12ZRNwCmVa3d2X5-rBQrbzq7f9aIDesiV")

print("🚀 Starting RukBot server...")
print(f"🧩 Using Drive folder ID: {GOOGLE_DRIVE_FOLDER_ID}")

# =====================================================
# 2️⃣ FASTAPI APP CONFIGURATION
# =====================================================
app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # allows embedding anywhere
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
# 4️⃣ KNOWLEDGE BASE INITIALIZATION
# =====================================================
print("📂 Loading knowledge base from Google Drive...")
try:
    knowledge_cache = load_google_folder_files(GOOGLE_DRIVE_FOLDER_ID)
    print(f"✅ Loaded {len(knowledge_cache)} files from knowledge base.")
except Exception as e:
    print(f"❌ Error loading knowledge base: {e}")
    knowledge_cache = {}

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
# 6️⃣ PDF EXTRACTION UTILITY
# =====================================================
def extract_text_from_pdf(filename):
    text = ""
    try:
        with fitz.open(filename) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Error reading {filename}: {e}")
    return text

# =====================================================
# 7️⃣ PROMPT GENERATION
# =====================================================
def build_prompt(user_message, documents_text):
    return f"""
You are RukBot — a casually brilliant AI trained on the RUKVEST and RUKSAK brand.

🗣️ Tone & Style:
- Friendly, like a helpful gym buddy
- Keep replies short, sharp, and easy to skim (mobile-friendly)
- Add emojis when helpful (but not overdone)
- Speak human: avoid fluff, repetition, or robotic-sounding replies

❌ Avoid:
- Greetings like “Hey there”, “Hi”, or “Hello”
- Salesy hype like “transform your body”, “biohack”, “game changer”
- Mentioning documents, sources, or file references
- Overloading with info — only answer what’s asked

🎯 Mission:
Help the customer make fast, confident decisions — clearly and authentically.
If unsure, respond:
🧠 “Great question! Let me check on that for you.”
📩 “You can also reach our team directly at team@ruksak.com — they’ve got your back!”

🧠 Customer asked:
"{user_message}"

📚 Relevant Knowledge:
"{documents_text[:12000]}"
"""

def format_prompt(user_message):
    global response_count
    user_message = (
        user_message.replace("rukvest", "RUKVEST")
        .replace("rukvests", "RUKVESTS")
        .replace("ruksak", "RUKSAK")
        .replace("ruksaks", "RUKSAKS")
    )
    documents_text = "\n\n".join(knowledge_cache.values())
    response_count += 1
    return build_prompt(user_message, documents_text)

# =====================================================
# 8️⃣ RESPONSE GENERATION
# =====================================================
def handle_unknown_question():
    return (
        "🧠 Great question! Let me check on that for you. "
        "In the meantime, you can reach our team at 📩 team@ruksak.com — they’ve got your back!"
    )

def get_full_response(user_input):
    prompt = format_prompt(user_input)
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "You are RukBot, the casually brilliant gym buddy AI. "
                        "Do NOT start with greetings. "
                        "Be sharp, real, and human — skip fluff and stay authentic."
                    )
                },
                {"role": "user", "content": prompt}
            ]
        )
        return response.choices[0].message.content.strip()
    except Exception as e:
        print(f"⚠️ OpenAI request failed: {e}")
        return handle_unknown_question()

# =====================================================
# 9️⃣ FASTAPI ROUTES
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

@app.post("/refresh-knowledge")
async def refresh_knowledge():
    global knowledge_cache
    try:
        print("🔄 Refreshing RukBot Knowledge Base...")
        knowledge_cache = load_google_folder_files(GOOGLE_DRIVE_FOLDER_ID)
        print("✅ Knowledge base refreshed successfully.")
        return JSONResponse({"status": "success", "message": "Knowledge base refreshed successfully."})
    except Exception as e:
        print(f"❌ Error refreshing knowledge base: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
