from utils.knowledge_base_operators import create_document_config, ingest_documents_dla
import json
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaIoBaseDownload
import io
from PyPDF2 import PdfReader
from typing import Tuple, Optional
import os.path
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.errors import HttpError


# If modifying these scopes, delete the file token.json.
SCOPES = ["https://www.googleapis.com/auth/drive.readonly"]


def read_text_file(file_id):
    """Reads a text file from Google Drive and prints its contents
    Args:
        file_id: ID of the file to read
    """
    creds = None
    if os.path.exists("token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("drive", "v3", credentials=creds)
        
        # Create a bytes IO object to store the file content
        request = service.files().get_media(fileId=file_id)
        file = io.BytesIO()
        downloader = MediaIoBaseDownload(file, request)
        
        # Download the file
        done = False
        while done is False:
            status, done = downloader.next_chunk()

        # Read the content
        file.seek(0)
        content = file.read().decode('utf-8')
        
        return content

    except HttpError as error:
        print(f"An error occurred: {error}")



def list_gdrive_files():
  """Shows basic usage of the Drive v3 API.
  Prints the names and ids of the first 10 files the user has access to.
  """
  creds = None
  # The file token.json stores the user's access and refresh tokens, and is
  # created automatically when the authorization flow completes for the first
  # time.
  if os.path.exists("token.json"):
    creds = Credentials.from_authorized_user_file("token.json", SCOPES)
  # If there are no (valid) credentials available, let the user log in.
  if not creds or not creds.valid:
    if creds and creds.expired and creds.refresh_token:
      creds.refresh(Request())
    else:
      flow = InstalledAppFlow.from_client_secrets_file(
          "credentials.json", SCOPES
      )
      creds = flow.run_local_server(port=0)
    # Save the credentials for the next run
    with open("token.json", "w") as token:
      token.write(creds.to_json())

  try:
    service = build("drive", "v3", credentials=creds)

    # Call the Drive v3 API
    results = (
        service.files()
        .list(pageSize=10, fields="nextPageToken, files(id, name)")
        .execute()
    )
    items = results.get("files", [])

    if not items:
      print("No files found.")
      return
    return items
  except HttpError as error:
    # TODO(developer) - Handle errors from drive API.
    print(f"An error occurred: {error}")


def get_pdf_from_drive(file_id) -> Tuple[Optional[bytes], Optional[str]]:
    """
    Downloads a PDF file from Google Drive and returns both raw bytes and extracted text
    
    Args:
        file_id (str): The ID of the file in Google Drive
    
    Returns:
        Tuple[Optional[bytes], Optional[str]]: Tuple containing:
            - Raw PDF bytes (or None if failed)
            - Extracted text content (or None if failed)
    """
    try:


        creds = None
        # The file token.json stores the user's access and refresh tokens, and is
        # created automatically when the authorization flow completes for the first
        # time.
        if os.path.exists("token.json"):
            creds = Credentials.from_authorized_user_file("token.json", SCOPES)
        # If there are no (valid) credentials available, let the user log in.
        if not creds or not creds.valid:
            if creds and creds.expired and creds.refresh_token:
                creds.refresh(Request())
            else:
                flow = InstalledAppFlow.from_client_secrets_file(
                    "credentials.json", SCOPES
                )
                creds = flow.run_local_server(port=0)
                # Save the credentials for the next run
                with open("token.json", "w") as token:
                    token.write(creds.to_json())



        # Initialize the Drive API service
        #creds = Credentials.from_authorized_user_file('credentials.json', ['https://www.googleapis.com/auth/drive.readonly'])
        service = build('drive', 'v3', credentials=creds)

        # Create a bytes stream to store the file
        file_stream = io.BytesIO()

        # Get the file from Drive
        request = service.files().get_media(fileId=file_id)
        downloader = MediaIoBaseDownload(file_stream, request)

        # Download the file
        done = False
        while not done:
            status, done = downloader.next_chunk()
            if status:
                print(f"Download progress: {int(status.progress() * 100)}%")

        # Get the raw PDF bytes
        pdf_bytes = file_stream.getvalue()
        
        # Reset stream position for text extraction
        file_stream.seek(0)

        # Extract text content
        pdf_reader = PdfReader(file_stream)
        text_content = ""
        
        # Extract text from all pages
        for page in pdf_reader.pages:
            text_content += page.extract_text() + "\n"

        return pdf_bytes, text_content.strip()

    except Exception as e:
        print(f"An error occurred: {str(e)}")
        return None, None






def build_document_config(document_id, document_content, source_name):
    
    metadata_source = {'key': 'source', 'value': { 'stringValue': source_name, 'type': 'STRING'}}
    metadata_list =[metadata_source]


    custom_inline_text_inline_metadata = create_document_config(
            data_source_type='CUSTOM',
            document_id=document_id,
            inline_content={
                'type': 'TEXT',
                'data': json.dumps(document_content)
            },
            metadata= metadata_list
    )

    return custom_inline_text_inline_metadata
