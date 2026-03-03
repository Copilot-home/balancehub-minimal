import os.path
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
import base64
import re

# If modifying these scopes, delete the file token.json.
SCOPES = ['https://www.googleapis.com/auth/gmail.modify']

def main():
    creds = None
    token_path = '/Users/andy/my_too_test/token.json'
    creds_path = '/Users/andy/my_too_test/credentials.json'

    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing token...")
            creds.refresh(Request())
            # Save the refreshed credentials
            with open(token_path, 'w') as token:
                token.write(creds.to_json())
        else:
            print("❌ Credentials invalid or need manual re-auth. Cannot run headless.")
            return

    try:
        service = build('gmail', 'v1', credentials=creds)

        # Search for WordPress emails
        print("🔍 Searching for 'WordPress' in Gmail...")
        results = service.users().messages().list(userId='me', q='WordPress', maxResults=10).execute()
        messages = results.get('messages', [])

        if not messages:
            print('No messages found.')
            return

        print(f"✅ Found {len(messages)} potential messages.")
        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id']).execute()
            snippet = m.get('snippet', '')
            subject = ''
            for header in m.get('payload', {}).get('headers', []):
                if header.get('name') == 'Subject':
                    subject = header.get('value')
            
            print(f"- Subject: {subject}")
            print(f"  Snippet: {snippet}")
            
            # Look for URLs in the snippet or body
            urls = re.findall(r'https?://[^\s<>"]+|www\.[^\s<>"]+', snippet)
            for url in urls:
                if 'wordpress.com' in url or 'apomega' in url:
                    print(f"  🌟 Potential URL: {url}")

    except Exception as error:
        print(f'An error occurred: {error}')

if __name__ == '__main__':
    main()
