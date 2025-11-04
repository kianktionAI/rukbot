from googleapiclient.discovery import build
from google.oauth2 import service_account

# Path to your service account file
SERVICE_ACCOUNT_FILE = 'service_account_rukbot.json'
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

# Authenticate
creds = service_account.Credentials.from_service_account_file(
    SERVICE_ACCOUNT_FILE, scopes=SCOPES
)
service = build('drive', 'v3', credentials=creds)

# Folder ID for RukBot knowledge base
FOLDER_ID = '12ZRNwCmVa3d2X5-rBQrbzq7f9aIDesiV'

# Try listing files
results = service.files().list(
    q=f"'{FOLDER_ID}' in parents",
    fields="files(id, name)"
).execute()

items = results.get('files', [])

if not items:
    print("⚠️ No files found in folder.")
else:
    print("✅ Files found in folder:")
    for item in items:
        print(f"📄 {item['name']} (ID: {item['id']})")
