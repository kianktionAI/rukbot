# rukbot.py

import os
import fitz  # PyMuPDF
import random
from dotenv import load_dotenv
from openai import OpenAI
from datetime import datetime
from pydrive2.auth import GoogleAuth
from pydrive2.drive import GoogleDrive
import gspread
from google.oauth2.service_account import Credentials

# Load environment variables
load_dotenv()

# Setup OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    project=os.getenv("OPENAI_PROJECT_ID")
)

# Globals
from drive_utils import load_google_folder_files  # make sure this import works

knowledge_cache = load_google_folder_files("12ZRNwCmVa3d2X5-rBQrbzq7f9aIDesiV")

greeting_used = False
response_count = 0

GREETINGS_FIRST = [
    "Hey legend",
    "G'day mate",
    "How’s it going, legend?",
    "Hey there 👋",
    "Welcome aboard 🚀"
]

GREETINGS_FOLLOWUP = [
    "",
    "Sure thing! 👍",
    "Here's what I’ve got for you: 👇",
    "You got it, let’s go 💪",
    "Happy to help!"
]

# Logging to Google Sheet
def log_to_google_sheet(question, response):
    try:
        creds = Credentials.from_service_account_file("service_account.json", scopes=["https://www.googleapis.com/auth/spreadsheets"])
        sheet = gspread.authorize(creds).open("RukBot Logs")
        worksheet = sheet.worksheet("Sheet1")
        worksheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            question,
            response
        ])
    except Exception as e:
        print("Logging to Google Sheet failed:", e)


# Extract PDF text
def extract_text_from_pdf(filename):
    text = ""
    try:
        with fitz.open(filename) as doc:
            for page in doc:
                text += page.get_text()
    except Exception as e:
        print(f"Error reading {filename}: {e}")
    return text

# Format prompt for OpenAI
def format_prompt(user_message):
    global greeting_used

    user_message = user_message.replace("rukvest", "RUKVEST").replace("rukvests", "RUKVESTS")
    user_message = user_message.replace("ruksak", "RUKSAK").replace("ruksaks", "RUKSAKS")

    documents_text = "\n\n".join(knowledge_cache.values())

    opener = random.choice(GREETINGS_FIRST) + "\n\n" if not greeting_used else ""
    greeting_used = True

    prompt = f"""
You are RukBot — a casually brilliant AI trained on the RUKVEST and RUKSAK brand.

Tone:
- Friendly, like a helpful gym buddy
- Keep replies short, clear, and mobile-friendly
- Use emojis to add warmth and clarity
- Use brand phrases like “Move with meaning”, “Start light and build”, and “We've got your back (literally)”
- Avoid fluff, repetition, and robotic language

Avoid:
- Salesy hype like “transform your body”, “biohack”, “game changer”
- Mentioning documents or sources

Start the message with:
{opener}

Customer asked:
"{user_message}"

Relevant Brand Knowledge:
"{documents_text[:12000]}"
"""
    return prompt

# Reset session
def reset_session():
    global greeting_used, response_count
    greeting_used = False
    response_count = 0

# Response streamer
def stream_response(user_input):
    prompt = format_prompt(user_input)

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are RukBot, the casually brilliant gym buddy AI."},
            {"role": "user", "content": prompt}
        ],
        stream=True
    )

    for chunk in response:
    try:
        content = chunk.choices[0].delta.content
        if content:
            yield content
    except AttributeError:
        pass





from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "RukBot is alive!"}

@app.post("/chat")
async def chat_endpoint(request: Request):
    data = await request.json()
    user_input = data.get("message", "")

    def generate():
        for chunk in stream_response(user_input):
            yield chunk

    return StreamingResponse(generate(), media_type="text/plain")

