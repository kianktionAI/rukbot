from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
import os
import json

SCOPES = ['https://www.googleapis.com/auth/drive.readonly']

def main():
    creds = None
    if os.path.exists('token.json'):
        print("Token already exists.")
        return

    # Load client secrets from environment variable
    client_config_str = os.getenv("GOOGLE_CLIENT_CONFIG")
    if not client_config_str:
        raise ValueError("Missing GOOGLE_CLIENT_CONFIG environment variable.")

    client_config = json.loads(client_config_str)

    flow = InstalledAppFlow.from_client_config(client_config, SCOPES)
    creds = flow.run_local_server(port=8080, access_type='offline', prompt='consent')

    # Save the token
    with open('token.json', 'w') as token_file:
        token_file.write(creds.to_json())
    print("token.json created successfully.")

if __name__ == '__main__':
    main()
