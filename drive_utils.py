from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from pdfminer.high_level import extract_text
import tempfile

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']
SERVICE_ACCOUNT_FILE = '/etc/secrets/service_account.json'  # Make sure this path is correct on Render

def load_google_folder_files(folder_id):
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
        mime_type = item['mimeType']

        request = service.files().get_media(fileId=file_id)
        fh = io.BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)

        if file_name.lower().endswith(".pdf"):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as temp_pdf:
                temp_pdf.write(fh.read())
                temp_pdf.flush()
                text = extract_text(temp_pdf.name)
                file_contents[file_name] = text
        else:
            file_contents[file_name] = fh.read().decode('utf-8')

    print(f"✅ Loaded {len(file_contents)} files from Google Drive.")
    return file_contents
