import os
import io
import tempfile
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
from pdfminer.high_level import extract_text

# =====================================================
# 1️⃣ CONFIGURATION
# =====================================================
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]

# Detect Render environment (uses injected secret path)
if os.getenv("RENDER"):
    SERVICE_ACCOUNT_FILE = "/etc/secrets/service_account.json"
else:
    SERVICE_ACCOUNT_FILE = "service_account_rukbot.json"

# =====================================================
# 2️⃣ GOOGLE DRIVE FILE LOADER
# =====================================================
def load_google_folder_files(folder_id: str):
    """
    Loads all readable text (PDF or plain text) from a Google Drive folder.
    Returns a dictionary: { filename: text_content }
    """
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=SCOPES
    )
    service = build("drive", "v3", credentials=creds)

    query = f"'{folder_id}' in parents and trashed = false"
    results = service.files().list(q=query, fields="files(id, name, mimeType)").execute()
    items = results.get("files", [])

    if not items:
        print("⚠️ No files found in Google Drive folder.")
        return {}

    file_contents = {}

    for item in items:
        file_id = item["id"]
        file_name = item["name"]
        mime_type = item["mimeType"]

        print(f"📄 Loading file: {file_name}")

        try:
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request)
            done = False
            while not done:
                status, done = downloader.next_chunk()
            fh.seek(0)

            # Extract text based on file type
            if file_name.lower().endswith(".pdf"):
                with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                    temp_pdf.write(fh.read())
                    temp_pdf.flush()
                    try:
                        text = extract_text(temp_pdf.name)
                        file_contents[file_name] = text.strip()
                    except Exception as e:
                        print(f"❌ Failed to extract text from {file_name}: {e}")
                        file_contents[file_name] = ""
            else:
                try:
                    file_contents[file_name] = fh.read().decode("utf-8").strip()
                except Exception as e:
                    print(f"❌ Failed to decode text from {file_name}: {e}")
                    file_contents[file_name] = ""

        except Exception as e:
            print(f"⚠️ Error downloading {file_name}: {e}")

    print(f"✅ Loaded {len(file_contents)} files from Google Drive.")
    return file_contents
