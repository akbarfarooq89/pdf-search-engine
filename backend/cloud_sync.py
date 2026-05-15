import os
import sys
import json
import time
from dotenv import load_dotenv

# Load .env file for local development
load_dotenv(os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), ".env"))

from supabase import create_client, Client
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

# Add current dir to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from parser import extract_text_from_file, categorize_document

# --- CONFIGURATION ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

# Files for Authentication
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "client_secrets.json")
TOKEN_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "token.json")

GDRIVE_FOLDER_ID = "1kw6Cs2kGEBcF4Y6kIeyXcdQho8UHRnRl" # Your shared folder ID
PDF_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "pdfs")

# Google Drive Scopes
SCOPES = ['https://www.googleapis.com/auth/drive.file']

# --- INITIALIZATION ---
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

print("Checking Google Drive credentials...")
def get_drive_service():
    creds = None
    if os.path.exists(TOKEN_FILE):
        print(f"Found {TOKEN_FILE}, loading credentials...")
        creds = Credentials.from_authorized_user_file(TOKEN_FILE, SCOPES)
    
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            print("Refreshing expired credentials...")
            creds.refresh(Request())
        else:
            print("Starting new authentication flow...")
            if not os.path.exists(CLIENT_SECRETS_FILE):
                print(f"ERROR: {CLIENT_SECRETS_FILE} not found.")
                sys.exit(1)
            flow = InstalledAppFlow.from_client_secrets_file(CLIENT_SECRETS_FILE, SCOPES)
            creds = flow.run_local_server(port=0)
        
        with open(TOKEN_FILE, 'w') as token:
            token.write(creds.to_json())

    print("Connecting to Google Drive API...")
    service = build('drive', 'v3', credentials=creds)
    print("Google Drive API connected successfully!")
    return service

drive_service = get_drive_service()

def upload_to_gdrive(filepath, filename):
    """Uploads a file to Google Drive with a progress bar."""
    print(f"  -> Uploading {filename}...")
    file_metadata = {
        'name': filename,
        'parents': [GDRIVE_FOLDER_ID] # Upload into your shared folder
    }
    media = MediaFileUpload(filepath, mimetype='application/pdf', resumable=True)
    
    request = drive_service.files().create(
        body=file_metadata, 
        media_body=media, 
        fields='id, webViewLink',
        supportsAllDrives=True
    )
    
    response = None
    while response is None:
        status, response = request.next_chunk()
        if status:
            print(f"     Progress: {int(status.progress() * 100)}%", end='\r')
    
    print(f"     Progress: 100% (Done!)")
    file_id = response.get('id')
    
    # Make the file public
    drive_service.permissions().create(
        fileId=file_id,
        body={'type': 'anyone', 'role': 'reader'},
        supportsAllDrives=True
    ).execute()
    
    # Get the shareable link
    file_info = drive_service.files().get(
        fileId=file_id, 
        fields='webViewLink',
        supportsAllDrives=True
    ).execute()
    return file_info.get('webViewLink')

def sync_all():
    print("\nStarting Cloud Sync (Google Drive + Supabase)")
    print("--------------------------------------------------")
    
    if not os.path.exists(PDF_DIR):
        print(f"Error: PDF directory not found at {PDF_DIR}")
        return

    count = 0
    for root, dirs, files in os.walk(PDF_DIR):
        for file in files:
            if not file.lower().endswith((".pdf", ".png", ".jpg", ".jpeg")):
                continue
                
            filepath = os.path.join(root, file)
            rel_path = os.path.relpath(filepath, PDF_DIR).replace('\\', '/')
            
            # 1. Check if already in Supabase
            try:
                res = supabase.table("documents").select("id").eq("filename", rel_path).execute()
                if res.data:
                    continue
            except Exception:
                pass # Continue if check fails
                
            print(f"\nProcessing: {rel_path}")
            
            # 2. Extract Text
            content = extract_text_from_file(filepath)
            title = os.path.basename(file).rsplit('.', 1)[0]
            
            # 3. Categorize
            univ, dtype = categorize_document(rel_path, title)
            
            # 4. Upload to Google Drive
            try:
                gdrive_link = upload_to_gdrive(filepath, file)
                
                # 5. Push to Supabase
                supabase.table("documents").insert({
                    "filename": rel_path,
                    "title": title,
                    "content": content,
                    "university": univ,
                    "doc_type": dtype,
                    "gdrive_link": gdrive_link
                }).execute()
                
                print(f"  [OK] Success: Saved to Cloud Database.")
                count += 1
            except Exception as e:
                print(f"  [ERROR] {e}")

    print("\n--------------------------------------------------")
    print(f"All done! Added {count} new files to the cloud.")

if __name__ == "__main__":
    print("Pre-checks complete. Starting sync_all process...")
    sync_all()
