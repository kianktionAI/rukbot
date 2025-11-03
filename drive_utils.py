import os
from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from pdfminer.high_level import extract_text
import tempfile

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# 👇 Checks if you're running on Render
if os.getenv("RENDER"):
    SERVICE_ACCOUNT_FILE = "/etc/secrets/service_account.json"
else:
    SERVICE_ACCOUNT_FILE = "service_account_rukbot.json"

def load_google_folder_files(folder_id):
    """
    Returns a dict: {filename: extracted_text}
    - PDFs: text extracted via pdfminer
    - Non-PDF text files: decoded as UTF-8
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

        if file_name.lower().endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                temp_pdf.write(fh.read())
                temp_pdf.flush()
                text = extract_text(temp_pdf.name)
                file_contents[file_name] = text
        else:
            try:
                file_contents[file_name] = fh.read().decode('utf-8')
            except Exception:
                # If decoding fails, store empty string rather than crashing
                file_contents[file_name] = ""

    print(f"✅ Loaded {len(file_contents)} files from Google Drive.")
    return file_contents
