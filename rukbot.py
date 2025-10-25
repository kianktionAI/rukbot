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
# 7️⃣ SYSTEM PROMPT — STRICT ACCURACY MODE
# =====================================================
SYSTEM_PROMPT = """
You are RUKBOT — the official support assistant for RUKSAK and RUKVEST.

🎯 PURPOSE:
Answer customer questions using ONLY verified information from the official RUKBOT FAQ and product documents.
If you are less than 90% confident in your answer or the information is not explicitly stated, DO NOT guess.
Instead, reply with this exact message:
"Hey legend, I’m not 100% sure on that one — best to flick a quick email to team@ruksak.com and they’ll look after you."

🧭 RULES:
1. Never invent or assume facts.
2. Never say "let me check" or imply you can look something up.
3. Keep replies short, friendly, and human — like a supportive gym buddy.
4. Use emojis naturally (💪 🎒 ✨ 💧).
5. Only use content clearly contained in the provided FAQ/product data.
6. If multiple answers exist, summarise briefly without assumptions.
7. If unsure or confidence <90%, always default to the email fallback.
"""

# =====================================================
# 8️⃣ PROMPT GENERATION
# =====================================================
def build_prompt(user_message, documents_text):
    return f"""
The user asked:
"{user_message}"

Here are the verified product and FAQ details you can use:
{documents_text[:12000]}

Remember:
- Use only the information above.
- If confidence <90%, respond with the fallback message.
- Maintain RUKBOT’s upbeat, friendly style.
"""

# =====================================================
# 9️⃣ TARGETED KNOWLEDGE RETRIEVAL
# =====================================================
def format_prompt(user_message):
    msg = user_message.lower()
    if "rukvest" in msg or "vest" in msg:
        relevant_docs = [
            knowledge_cache.get("RUKVEST_Product_Info.pdf", ""),
            knowledge_cache.get("RukBot FAQ.pdf", ""),
            knowledge_cache.get("RUKBOT_Product_Comparison_Cheat_Sheet.pdf", "")
        ]
    elif "ruksak" in msg or "rucksack" in msg or "bag" in msg:
        relevant_docs = [
            knowledge_cache.get("RUKSAK_Product_Info.pdf", ""),
            knowledge_cache.get("RukBot FAQ.pdf", ""),
            knowledge_cache.get("RUKBOT_Product_Comparison_Cheat_Sheet.pdf", "")
        ]
    elif "rukbrik" in msg or "brick" in msg:
        relevant_docs = [
            knowledge_cache.get("RUKBRIK_Product_Info.pdf", ""),
            knowledge_cache.get("RukBot FAQ.pdf", "")
        ]
    else:
        relevant_docs = [
            knowledge_cache.get("RukBot FAQ.pdf", ""),
            knowledge_cache.get("RUKBOT_Product_Comparison_Cheat_Sheet.pdf", "")
        ]

    documents_text = "\n\n".join([doc for doc in relevant_docs if doc])
    return build_prompt(user_message, documents_text)

# =====================================================
# 🔟 RESPONSE GENERATION WITH CONFIDENCE CHECK
# =====================================================
def get_full_response(user_input):
    prompt = format_prompt(user_input)
    fallback_msg = (
        "Hey legend, I’m not 100% sure on that one — best to flick a quick email "
        "to team@ruksak.com and they’ll look after you."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.0,
            logprobs=True,
            top_p=1
        )
        answer = response.choices[0].message.content.strip()

        logprobs = response.choices[0].logprobs
        if logprobs and hasattr(logprobs, "content"):
            avg_conf = sum(token.logprob for token in logprobs.content) / len(logprobs.content)
            confidence = min(1.0, max(0.0, 1 + (avg_conf / 5)))
            if confidence < 0.9:
                print(f"⚠️ Low confidence detected ({confidence:.2f}), using fallback.")
                return fallback_msg

        uncertain_phrases = [
            "let me check", "not sure", "maybe", "i think", "possibly", "i’ll find out"
        ]
        if any(p in answer.lower() for p in uncertain_phrases):
            return fallback_msg

        return answer or fallback_msg

    except Exception as e:
        print(f"⚠️ OpenAI request failed: {e}")
        return fallback_msg

# =====================================================
# 11️⃣ REFRESH KNOWLEDGE ENDPOINT
# =====================================================
@app.get("/refresh_knowledge")
async def refresh_knowledge():
    """Reload knowledge base files from Google Drive"""
    global knowledge_cache
    try:
        knowledge_cache = load_google_folder_files(GOOGLE_DRIVE_FOLDER_ID)
        print(f"✅ Refreshed knowledge base with {len(knowledge_cache)} files.")
        return {"status": "success", "files_loaded": len(knowledge_cache)}
    except Exception as e:
        print(f"❌ Failed to refresh knowledge base: {e}")
        return {"status": "error", "message": str(e)}

# =====================================================
# ✅ HEALTH CHECK ENDPOINT
# =====================================================
@app.get("/check")
async def check():
    return {"status": "ok"}
