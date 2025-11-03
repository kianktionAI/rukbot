import os
import math
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
GOOGLE_DRIVE_FOLDER_ID = os.getenv(
    "GOOGLE_DRIVE_FOLDER_ID", "12ZRNwCmVa3d2X5-rBQrbzq7f9aIDesiV"
)

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
# 7️⃣ PROMPT GENERATION
# =====================================================
def build_prompt(user_message, documents_text):
    return f"""
You are RukBot — the casually brilliant AI trained on the RUKVEST and RUKSAK brand.

🗣️ Tone & Style:
- Friendly, like a helpful gym buddy
- Short, sharp, and mobile-friendly
- Add emojis sparingly for emphasis
- Speak human — no corporate jargon, no sales pitch

❌ Avoid:
- Greetings (“Hey there”, “Hi”, “Hello”)
- Mentioning sources, documents, or PDFs
- Overly long or robotic answers

🎯 Mission:
Give clear, confident answers to help customers quickly.
If uncertain, reply:
“I’m not 100% on that one — best to check with our team at team@ruksak.com — they’ve got your back!”

🧠 Customer asked:
"{user_message}"

📚 Relevant Knowledge:
"{documents_text[:12000]}"
"""

# =====================================================
# 8️⃣ TARGETED KNOWLEDGE RETRIEVAL
# =====================================================
def format_prompt(user_message):
    global response_count
    msg = user_message.lower()
    response_count += 1

    # Pick which docs to feed based on what they asked about
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
        # generic fallback
        relevant_docs = [
            knowledge_cache.get("RukBot FAQ.pdf", ""),
            knowledge_cache.get("RUKBOT_Product_Comparison_Cheat_Sheet.pdf", "")
        ]

    documents_text = "\n\n".join([doc for doc in relevant_docs if doc])
    return build_prompt(user_message, documents_text)

# =====================================================
# 9️⃣ COSINE SIMILARITY (pure Python, no numpy)
# =====================================================
def cosine_sim(vec1, vec2):
    """
    vec1, vec2 are lists of floats.
    returns float between 0 and 1.
    """
    if not vec1 or not vec2:
        return 0.0

    # dot product
    dot = 0.0
    for a, b in zip(vec1, vec2):
        dot += a * b

    # magnitudes
    mag1 = math.sqrt(sum(a * a for a in vec1))
    mag2 = math.sqrt(sum(b * b for b in vec2))
    if mag1 == 0 or mag2 == 0:
        return 0.0

    return dot / (mag1 * mag2)

# =====================================================
# 🔟 EMBEDDINGS (returns plain Python list)
# =====================================================
def get_embedding(text):
    try:
        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        # OpenAI returns a list of floats already
        return emb.data[0].embedding
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
        # fallback: zero vector same length as model output (1536 dims)
        return [0.0] * 1536

# =====================================================
# 1️⃣1️⃣ MAIN RESPONSE GENERATION
# =====================================================
def get_full_response(user_input):
    text = user_input.lower()

    # ❌ Disallow nonsense cross-product combos
    invalid_pairs = [
        ("rukvest", "rukbrik"),
        ("rukbrik", "rukvest"),
        ("rukvest", "rukblock"),
        ("rukblock", "rukvest"),
    ]
    for a, b in invalid_pairs:
        if a in text and b in text:
            print("⚠️ Cross-product combo detected — triggering fallback.")
            return (
                "That combo doesn’t sound right — best to check with our team at 📩 "
                "team@ruksak.com — they’ve got your back!"
            )

    # Build the prompt we'll feed to the model
    prompt = format_prompt(user_input)

    # Pull just the knowledge part from that prompt
    # so we can judge how relevant it is
    if "📚 Relevant Knowledge:" in prompt:
        document_texts = prompt.split("📚 Relevant Knowledge:")[-1].strip()
    else:
        document_texts = ""

    # --- semantic confidence gate ---
    user_emb = get_embedding(user_input)
    doc_emb = get_embedding(document_texts)
    similarity = cosine_sim(user_emb, doc_emb)
    print(f"🧭 Semantic match confidence: {similarity:.3f}")

    if similarity < 0.75:
        print("⚠️ Low semantic match — diverting to email fallback.")
        return (
            "I’m not 100% on that one — best to check with our team at 📩 "
            "team@ruksak.com — they’ve got your back!"
        )

    # --- system message (tone & safety) ---
    strict_system_message = (
        "You are RukBot — the casually brilliant AI for RUKVEST & RUKSAK. "
        "You must only answer using the verified FAQ and product information provided. "
        "If you cannot confidently find the answer, always reply with:\n"
        "“I’m not 100% on that one — best to check with our team at team@ruksak.com "
        "— they’ve got your back!”\n\n"
        "Maintain RUKBOT brand tone: concise, confident, kind, and never robotic. "
        "Never open with greetings. Never mention 'documents' or 'sources'. "
        "Use emojis sparingly to support clarity or positivity."
    )

    try:
        # Ask OpenAI for the actual answer
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": strict_system_message},
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
        )

        answer = response.choices[0].message.content.strip()

        # If the model itself sounds unsure, force fallback
        unsure_triggers = [
            "not sure",
            "unsure",
            "uncertain",
            "don’t know",
            "don't know",
            "can't tell",
        ]
        if any(term in answer.lower() for term in unsure_triggers):
            print("⚠️ Detected uncertainty phrase — fallback triggered.")
            return (
                "I’m not 100% on that one — best to check with our team at 📩 "
                "team@ruksak.com — they’ve got your back!"
            )

        # Make sure we *always* give a contact path in the final answer
        if "team@ruksak.com" not in answer.lower():
            answer += (
                " 📩 If you want to double-check, our team’s always happy to help "
                "at team@ruksak.com — they’ve got your back!"
            )

        return answer

    except Exception as e:
        print(f"⚠️ OpenAI request failed: {e}")
        return (
            "Something went a bit sideways there — best to check with our team at "
            "📩 team@ruksak.com — they’ve got your back!"
        )

# =====================================================
# 1️⃣2️⃣ FASTAPI ROUTES
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
        return JSONResponse(
            {"status": "success", "message": "Knowledge base refreshed successfully."}
        )
    except Exception as e:
        print(f"❌ Error refreshing knowledge base: {e}")
        return JSONResponse(
            {"status": "error", "message": str(e)},
            status_code=500
        )
