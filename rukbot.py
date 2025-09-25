# rukbot.py

import os
import fitz  # PyMuPDF
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles

# Load environment variables
load_dotenv()

# FastAPI app
app = FastAPI()
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

# Setup OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    project=os.getenv("OPENAI_PROJECT_ID")
)

# Load Google Drive docs
from drive_utils import load_google_folder_files
knowledge_cache = load_google_folder_files("12ZRNwCmVa3d2X5-rBQrbzq7f9aIDesiV")

# Globals
response_count = 0  # tracks first vs follow-up


# --------------------------------------------------
# Logging to Google Sheet
# --------------------------------------------------
def log_to_google_sheet(question, response):
    try:
        creds = Credentials.from_service_account_file(
            "/etc/secrets/service_account.json",
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
        print("⚠️ Logging to Google Sheet failed:", e)


# --------------------------------------------------
# PDF Text Extractor
# --------------------------------------------------
def extract_text_from_pdf(filename):
    text = ""
    try:
        with fitz.open(filename) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Error reading {filename}: {e}")
    return text


# --------------------------------------------------
# Prompt Builder
# --------------------------------------------------
def build_prompt(user_message, documents_text):
    return f"""
You are RukBot — a casually brilliant AI trained on the RUKVEST and RUKSAK brand.

🗣️ Tone & Style:
- Friendly, like a helpful gym buddy
- Keep replies short, sharp, and easy to skim (mobile-friendly)
- Add emojis when helpful (but not overdone)
- Use brand phrases like “Move with meaning”, “Start light and build”, and “We’ve got your back (literally)”
- Speak human: avoid fluff, repetition, or robotic-sounding replies

❌ Avoid:
- Salesy hype like “transform your body”, “biohack”, “game changer”
- Mentioning documents, sources, or file references
- Overloading with info — only answer what’s asked

🎯 Your mission:
- Help the customer make fast, confident decisions  
- Be clear, helpful, and aligned with brand tone  
- Never make things up — if unsure, say:  

🧠 “Great question! Let me check on that for you.”  
📩 You can also reach our team directly at team@ruksak.com — they’ve got your back!

🧠 Customer asked:
"{user_message}"

📚 Relevant Brand Knowledge:
"{documents_text[:12000]}"
"""


def format_prompt(user_message):
    global response_count

    # Brand-specific corrections
    user_message = user_message.replace("rukvest", "RUKVEST").replace("rukvests", "RUKVESTS")
    user_message = user_message.replace("ruksak", "RUKSAK").replace("ruksaks", "RUKSAKS")

    documents_text = "\n\n".join(knowledge_cache.values())
    response_count += 1

    return build_prompt(user_message, documents_text)


# --------------------------------------------------
# Session Reset
# --------------------------------------------------
def reset_session():
    global response_count
    response_count = 0


# --------------------------------------------------
# Routes
# --------------------------------------------------

@app.get("/check")
async def check():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request):
    reset_session()
    return templates.TemplateResponse("chat.html", {"request": request})


@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_input = data.get("message", "")

    prompt = format_prompt(user_input)
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are RukBot, the casually brilliant gym buddy AI."},
                {"role": "user", "content": prompt}
            ]
        )
        reply = response.choices[0].message.content

    except Exception as e:
        print("⚠️ OpenAI request failed:", e)
        reply = "⚠️ Oops, something went wrong."

    # Log to Google Sheets
    log_to_google_sheet(user_input, reply)

    return {"response": reply}


@app.get("/widget", response_class=HTMLResponse)
async def get_widget(request: Request):
    reset_session()
    return templates.TemplateResponse("rukbot-widget.html", {"request": request})
