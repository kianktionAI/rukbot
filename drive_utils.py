import os
import io
import fitz  # PyMuPDF
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# 👇 Detect Render vs Local
if os.getenv("RENDER"):
    SERVICE_ACCOUNT_FILE = "/etc/secrets/service_account.json"
else:
    SERVICE_ACCOUNT_FILE = "service_account_rukbot.json"


def extract_text_from_pdf(pdf_bytes):
    """Extract text from a PDF file using PyMuPDF (fitz)."""
    text = ""
    try:
        with fitz.open(stream=pdf_bytes, filetype="pdf") as doc:
            for page in doc:
                page_text = page.get_text("text")
                if page_text.strip():
                    text += page_text + "\n"
    except Exception as e:
        print(f"⚠️ PDF extraction failed: {e}")
    return text.strip()


def load_google_folder_files(folder_id):
    """
    Loads all files from a Google Drive folder and returns a dict:
    {filename: extracted_text}
    """
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build('drive', 'v3', credentials=creds)

    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    items = results.get('files', [])

    file_contents = {}

    for item in items:
        file_id = item['id']
        file_name = item['name']

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            _, done = downloader.next_chunk()
        fh.seek(0)

        # Extract text depending on file type
        if file_name.lower().endswith(".pdf"):
            text = extract_text_from_pdf(fh.read())
        else:
            try:
                text = fh.read().decode('utf-8', errors='ignore')
            except Exception:
                text = ""

        file_contents[file_name] = text
        print(f"✅ Loaded {file_name} ({len(text)} chars)")

    print(f"📚 Total files loaded: {len(file_contents)}")
    return file_contents


# --------------------------
# 🔹 Literal Search Helper
# --------------------------

def chunk_text(text, max_chunk_size=1000, overlap=100):
    """Split text into overlapping chunks for better retrieval."""
    chunks = []
    start = 0
    while start < len(text):
        end = start + max_chunk_size
        chunks.append(text[start:end])
        start += max_chunk_size - overlap
    return chunks


def search_drive_for_answer(query, folder_id):
    """Searches Drive files for a matching chunk of text related to the query."""
    print(f"🔍 Searching Drive for query: {query}")
    files = load_google_folder_files(folder_id)
    relevant_chunks = []

    for file_name, text in files.items():
        chunks = chunk_text(text)
        for chunk in chunks:
            if query.lower() in chunk.lower():
                relevant_chunks.append(f"📄 {file_name}:\n{chunk.strip()}")

    if relevant_chunks:
        print(f"✅ Found {len(relevant_chunks)} matching chunks.")
        return relevant_chunks[0][:1500]
    else:
        print("⚠️ No relevant information found.")
        return None
