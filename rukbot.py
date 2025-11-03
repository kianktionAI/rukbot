import os
import math
import heapq
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

from drive_utils import load_google_folder_files, search_drive_for_answer

# =====================================================
# 1️⃣ ENVIRONMENT SETUP
# =====================================================
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
OPENAI_PROJECT_ID = os.getenv("OPENAI_PROJECT_ID")
GOOGLE_DRIVE_FOLDER_ID = os.getenv("GOOGLE_DRIVE_FOLDER_ID", "12ZRNwCmVa3d2X5-rBQrbzq7f9aIDesiV")

print("🚀 Starting RukBot server...")
print(f"🧩 Using Drive folder ID: {GOOGLE_DRIVE_FOLDER_ID}")

CHUNK_SIZE = 800
CHUNK_OVERLAP = 120
TOP_K = 6
MIN_SIMILARITY = 0.20

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
client = OpenAI(api_key=OPENAI_API_KEY, project=OPENAI_PROJECT_ID)

# =====================================================
# 4️⃣ KNOWLEDGE BASE: LOAD + CHUNK + EMBED
# =====================================================
def chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP):
    chunks, start = [], 0
    n = len(text)
    step = max(1, size - overlap)
    while start < n:
        end = min(n, start + size)
        chunks.append(text[start:end])
        start += step
    return chunks


def cosine_similarity(a, b):
    dot = 0.0
    na = 0.0
    nb = 0.0
    for xa, xb in zip(a, b):
        dot += xa * xb
        na += xa * xa
        nb += xb * xb
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (math.sqrt(na) * math.sqrt(nb))


def get_embedding_vec(text: str):
    try:
        resp = client.embeddings.create(model="text-embedding-3-small", input=text)
        return resp.data[0].embedding
    except Exception as e:
        print(f"⚠️ Embedding error: {e}")
        return []


def build_knowledge_index(file_dict):
    index = {"chunks": []}
    total_chunks = 0
    for filename, content in file_dict.items():
        if not content or not content.strip():
            continue
        parts = chunk_text(content)
        for i, part in enumerate(parts):
            emb = get_embedding_vec(part)
            index["chunks"].append(
                {
                    "filename": filename,
                    "chunk_index": i,
                    "text": part,
                    "embedding": emb,
                }
            )
            total_chunks += 1
    print(f"✅ Knowledge index built: {len(file_dict)} files → {total_chunks} chunks.")
    return index


print("📂 Loading raw knowledge from Google Drive...")
try:
    knowledge_files = load_google_folder_files(GOOGLE_DRIVE_FOLDER_ID)
    knowledge_index = build_knowledge_index(knowledge_files)
except Exception as e:
    print(f"❌ Error preparing knowledge base: {e}")
    knowledge_files = {}
    knowledge_index = {"chunks": []}


# =====================================================
# 5️⃣ GOOGLE SHEET LOGGING
# =====================================================
def log_to_google_sheet(question, response):
    try:
        creds_path = "/etc/secrets/service_account.json" if os.getenv("RENDER") else "service_account_rukbot.json"
        creds = Credentials.from_service_account_file(
            creds_path, scopes=["https://www.googleapis.com/auth/spreadsheets"]
        )
        sheet = gspread.authorize(creds).open("RukBot Logs")
        worksheet = sheet.worksheet("Sheet1")
        worksheet.append_row([datetime.now().strftime("%Y-%m-%d %H:%M:%S"), question, response])
    except Exception as e:
        print(f"⚠️ Logging to Google Sheet failed: {e}")


# =====================================================
# 6️⃣ RETRIEVAL
# =====================================================
PRODUCT_HINTS = {
    "rukvest": ["RUKVEST", "RUKVEST_Product_Info.pdf"],
    "vest": ["RUKVEST", "RUKVEST_Product_Info.pdf"],
    "ruksak": ["RUKSAK", "RUKSAK_Product_Info.pdf"],
    "bag": ["RUKSAK", "RUKSAK_Product_Info.pdf"],
    "rucksack": ["RUKSAK", "RUKSAK_Product_Info.pdf"],
    "rukbrik": ["RUKBRIK", "RUKBRIK_Product_Info.pdf"],
    "brick": ["RUKBRIK", "RUKBRIK_Product_Info.pdf"],
}


def candidate_chunks(user_text: str):
    msg = user_text.lower()
    preferred_files = set()
    for key, hints in PRODUCT_HINTS.items():
        if key in msg:
            for h in hints:
                preferred_files.add(h)
    if not preferred_files:
        return knowledge_index["chunks"]

    filtered = [
        c
        for c in knowledge_index["chunks"]
        if any(h.lower() in c["filename"].lower() or h.lower() in c["text"].lower() for h in preferred_files)
    ]
    return filtered if filtered else knowledge_index["chunks"]


def retrieve(user_text: str, top_k: int = TOP_K):
    q_emb = get_embedding_vec(user_text)
    if not q_emb:
        return []
    cands = candidate_chunks(user_text)
    scored = []
    for c in cands:
        emb = c.get("embedding", [])
        if not emb:
            continue
        sim = cosine_similarity(q_emb, emb)
        scored.append((sim, c))
    return heapq.nlargest(top_k, scored, key=lambda x: x[0])


# =====================================================
# 7️⃣ PROMPT & RESPONSE
# =====================================================
def build_prompt(user_message, context_snippets):
    joined = "\n\n---\n".join([f"[{c['filename']} #{c['chunk_index']}] {c['text']}" for c in context_snippets])
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
If uncertain, reply exactly with:
“I’m not 100% on that one — best to check with our team at team@ruksak.com — they’ve got your back!”

🧠 Customer asked:
"{user_message}"

📚 Relevant Knowledge (internal notes):
{joined[:12000]}
"""


def get_full_response(user_input):
    text = user_input.lower()

    invalid_pairs = [
        ("rukvest", "rukbrik"),
        ("rukbrik", "rukvest"),
        ("rukvest", "rukblock"),
        ("rukblock", "rukvest"),
    ]
    for a, b in invalid_pairs:
        if a in text and b in text:
            print("⚠️ Cross-product combo detected — triggering fallback.")
            return "That combo doesn’t sound right — best to check with our team at 📩 team@ruksak.com — they’ve got your back!"

    literal_match = search_drive_for_answer(user_input, GOOGLE_DRIVE_FOLDER_ID)
    if literal_match:
        print("✅ Found direct text match from Drive chunk search.")
        return literal_match

    top = retrieve(user_input, TOP_K)
    if not top:
        print("⚠️ Retrieval returned no results — fallback.")
        return "I’m not 100% on that one — best to check with our team at 📩 team@ruksak.com — they’ve got your back!"

    best_score = top[0][0] if top else 0.0
    print(f"🧭 Best semantic match: {best_score:.3f}")

    if best_score < MIN_SIMILARITY:
        print("⚠️ Low semantic match — using forced contextual response.")
        context = [c for _, c in top]
        prompt = build_prompt(user_input, context)
    else:
        context = [c for _, c in top]
        prompt = build_prompt(user_input, context)

    system_message = (
        "You are RukBot — the casually brilliant AI for RUKVEST & RUKSAK. "
        "Only answer using the information provided. "
        "If you cannot confidently find the answer, reply exactly with: "
        "“I’m not 100% on that one — best to check with our team at team@ruksak.com — they’ve got your back!” "
        "Tone: concise, confident, kind. No greetings or source mentions."
    )

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": system_message}, {"role": "user", "content": prompt}],
            temperature=0.4,
        )
        answer = response.choices[0].message.content.strip()

        unsure_triggers = ["not sure", "unsure", "uncertain", "don’t know", "can't tell"]
        if any(term in answer.lower() for term in unsure_triggers):
            print("⚠️ Detected uncertainty — fallback.")
            return "I’m not 100% on that one — best to check with our team at 📩 team@ruksak.com — they’ve got your back!"

        if "team@ruksak.com" not in answer.lower() and any(k in user_input.lower() for k in ["contact", "help", "support", "email"]):
            answer += " 📩 If you want to double-check, our team’s always happy to help at team@ruksak.com — they’ve got your back!"
        return answer
    except Exception as e:
        print(f"⚠️ OpenAI request failed: {e}")
        return "Something went a bit sideways there — best to check with our team at 📩 team@ruksak.com — they’ve got your back!"


# =====================================================
# 🔟 FASTAPI ROUTES
# =====================================================
@app.get("/check")
async def check():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse)
async def get_chat(request: Request):
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
    return templates.TemplateResponse("rukbot-widget.html", {"request": request})


@app.post("/refresh-knowledge")
async def refresh_knowledge():
    global knowledge_files, knowledge_index
    try:
        print("🔄 Refreshing RukBot Knowledge Base...")
        knowledge_files = load_google_folder_files(GOOGLE_DRIVE_FOLDER_ID)
        knowledge_index = build_knowledge_index(knowledge_files)
        print("✅ Knowledge base refreshed successfully.")
        return JSONResponse({"status": "success", "message": "Knowledge base refreshed successfully."})
    except Exception as e:
        print(f"❌ Error refreshing knowledge base: {e}")
        return JSONResponse({"status": "error", "message": str(e)}, status_code=500)
