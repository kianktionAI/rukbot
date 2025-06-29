import os
import fitz  # PyMuPDF
from openai import OpenAI
from dotenv import load_dotenv
from pydrive.auth import GoogleAuth
from pydrive.drive import GoogleDrive
import random

# Load environment variables
load_dotenv()
from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

def log_to_google_sheet(question, response):
    try:
        creds = Credentials.from_service_account_file("service_account.json", scopes=["https://www.googleapis.com/auth/spreadsheets"])
        sheet = gspread.authorize(creds).open("RukBot Logs")  # Make sure this matches your Google Sheet name
        worksheet = sheet.worksheet("Sheet1")  # And this matches your tab
        worksheet.append_row([
            datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            question,
            response
        ])
    except Exception as e:
        print("Logging to Google Sheet failed:", e)

# Setup OpenAI client
client = OpenAI(
    api_key=os.getenv("OPENAI_API_KEY"),
    project=os.getenv("OPENAI_PROJECT_ID")
)

# Globals
knowledge_cache = {}
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

# Load files from Google Drive
def load_knowledge_from_drive():
    print("Loading knowledge base from Google Drive...")
    gauth = GoogleAuth()
    gauth.LocalWebserverAuth()
    drive = GoogleDrive(gauth)

    folder_id = "12ZRNwCmVa3d2X5-rBQrbzq7f9aIDesiV"
    file_list = drive.ListFile({'q': f"'{folder_id}' in parents and trashed=false"}).GetList()

    for file in file_list:
        if file['title'].endswith(".pdf"):
            file.GetContentFile(file['title'])
            doc_text = extract_text_from_pdf(file['title'])
            knowledge_cache[file['title']] = doc_text
            os.remove(file['title'])

    print(f"Loaded {len(knowledge_cache)} files into memory.")

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

    # Brand consistency
    user_message = user_message.replace("rukvest", "RUKVEST").replace("rukvests", "RUKVESTS")
    user_message = user_message.replace("ruksak", "RUKSAK").replace("ruksaks", "RUKSAKS")

    documents_text = "\n\n".join(knowledge_cache.values())

    # Greeting logic
    if not greeting_used:
        opener = random.choice(GREETINGS_FIRST) + "\n\n"
        greeting_used = True
    else:
        opener = ""

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
\"{user_message}\"

Relevant Brand Knowledge:
\"{documents_text[:12000]}\"
"""
    return prompt


# Reset session manually (optional)
def reset_session():
    global greeting_used, response_count
    greeting_used = False
    response_count = 0

# Response streamer
def stream_response(message):
    global response_count
    if not knowledge_cache:
        load_knowledge_from_drive()

    prompt = format_prompt(message)
    response_count += 1
    buffer = ""

try:
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": prompt},
            {"role": "user", "content": message}
        ],
        stream=True
    )

    for chunk in response:
        if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
            content = chunk.choices[0].delta.content
            buffer += content
            yield content

except Exception as e:
    print(f"Error while streaming response: {e}")



# ✅ Log once the full response has streamed
log_to_google_sheet(message, buffer)


        if response_count % 5 == 0:
            yield "\n\n❓ Not quite right? Drop us a line at [team@ruksak.com](mailto:team@ruksak.com) — we’re happy to help! 💌"

    except Exception as e:
        yield f"Oops! Something went wrong while chatting with RukBot: {str(e)}"
