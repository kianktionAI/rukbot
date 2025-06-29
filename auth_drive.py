from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import pickle
import os
import json

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def main():
    creds = None
    if os.path.exists('token.json'):
        print("Token already exists.")
        return

    flow = InstalledAppFlow.from_client_secrets_file(
        'credentials.json', SCOPES
    )
    creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')

    # Save the token
    with open('token.json', 'w') as token_file:
        token_file.write(creds.to_json())
    print("token.json created successfully.")

if __name__ == '__main__':
    main()
