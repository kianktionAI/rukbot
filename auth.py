import os
import json
import pickle
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build

# If modifying these scopes, delete the token.pickle file.
SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def authenticate_google_drive():
    creds = None
    # Load credentials from token.pickle if it exists
    if os.path.exists('token.pickle'):
        with open('token.pickle', 'rb') as token:
            creds = pickle.load(token)

    # If no valid creds, start login flow
    if not creds or not creds.valid:
        flow = InstalledAppFlow.from_client_secrets_file(
            'credentials.json', SCOPES)
        creds = flow.run_local_server(port=8080)

        # Save the credentials for next run
        with open('token.pickle', 'wb') as token:
            pickle.dump(creds, token)

    return build('drive', 'v3', credentials=creds)

if __name__ == '__main__':
    service = authenticate_google_drive()
    results = service.files().list(pageSize=10, fields="files(id, name)").execute()
    items = results.get('files', [])

    if not items:
        print('No files found.')
    else:
        print('Files:')
        for item in items:
            print(f"{item['name']} ({item['id']})")
