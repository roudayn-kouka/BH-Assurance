import os
import os.path
import base64
import time
import re
from email.mime.text import MIMEText
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from bs4 import BeautifulSoup
from pymongo import MongoClient, errors
from bson.objectid import ObjectId
from datetime import datetime
from mongodb_conn import append_message_to_conversation, update_conversation_status

# If modifying these scopes, delete the file token.json.
# 'https://www.googleapis.com/auth/gmail.readonly' is sufficient for reading.
SCOPES = [
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/gmail.modify",
]

# MongoDB URI (Update this with your actual connection string)
MONGODB_URI = "mongodb://localhost:27017/"


def get_gmail_service():
    """Authenticates the user and returns the Gmail API service object."""
    creds = None
    # The file token.json stores the user's access and refresh tokens.
    if os.path.exists("./token.json"):
        creds = Credentials.from_authorized_user_file("token.json", SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(
                "./credentials.json", SCOPES
            )
            creds = flow.run_local_server(port=0)
        # Save the credentials for the next run
        with open("token.json", "w") as token:
            token.write(creds.to_json())

    try:
        service = build("gmail", "v1", credentials=creds)
        return service
    except HttpError as error:
        print(f"An error occurred: {error}")
        return None


def get_conversation_id_by_client_id(client_id: str):
    """Finds an existing conversation ID for a given client."""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client.get_database("bh-assurance")
        conversations_collection = db["conversations"]

        # Search for an existing conversation for the client.
        # You might want to add a filter for "open" or "ongoing" conversations
        # in a real application.
        conversation_doc = conversations_collection.find_one(
            {"client_id": ObjectId(client_id)}
        )

        if conversation_doc:
            return conversation_doc["_id"]
        else:
            return None
    except errors.ServerSelectionTimeoutError as err:
        print("❌ MongoDB connection failed:", err)
        return None
    except Exception as e:
        print(f"❌ Error finding conversation for client {client_id}: {e}")
        return None
    finally:
        if "client" in locals() and client:
            client.close()


def get_client_id_by_email(email: str):
    """Finds a client ID in the clients collection based on their email address."""
    try:
        client = MongoClient(MONGODB_URI, serverSelectionTimeoutMS=5000)
        db = client.get_database("bh-assurance")
        clients_collection = db["clients"]

        client_doc = clients_collection.find_one({"email": email})

        if client_doc:
            return client_doc["_id"]
        else:
            return None
    except errors.ServerSelectionTimeoutError as err:
        print("❌ MongoDB connection failed:", err)
        return None
    except Exception as e:
        print(f"❌ Error finding client by email: {e}")
        return None
    finally:
        if "client" in locals() and client:
            client.close()


def read_emails_last_24h(service):
    """
    Reads unread emails sent in the last 24 hours and prints their subject and body.
    Marks them as read after processing.
    """
    try:
        # Search for unread messages sent within the last 24 hours.
        # 'q' is a query string with search operators.
        # 'is:unread' filters for unread emails.
        # 'newer_than:1d' filters for emails received in the last 1 day (24 hours).
        results = (
            service.users()
            .messages()
            .list(userId="me", q="is:unread newer_than:1d")
            .execute()
        )
        messages = results.get("messages", [])

        if not messages:
            print("No new messages found from the last 24 hours.")
        else:
            print(f"Found {len(messages)} new messages. Processing...")
            for message in messages:
                msg_id = message["id"]
                msg = (
                    service.users()
                    .messages()
                    .get(userId="me", id=msg_id, format="full")
                    .execute()
                )

                # Extract headers for subject and sender
                headers = msg["payload"]["headers"]
                subject = next(
                    (
                        header["value"]
                        for header in headers
                        if header["name"] == "Subject"
                    ),
                    "No Subject",
                )
                sender = next(
                    (header["value"] for header in headers if header["name"] == "From"),
                    "Unknown Sender",
                )

                # Decode the message body
                body_parts = msg["payload"].get("parts", [])
                body = ""
                for part in body_parts:
                    if part["mimeType"] == "text/plain":
                        data = part["body"]["data"]
                        body += base64.urlsafe_b64decode(data).decode("utf-8")
                    elif part["mimeType"] == "text/html":
                        data = part["body"]["data"]
                        html = base64.urlsafe_b64decode(data).decode("utf-8")
                        body += BeautifulSoup(html, "html.parser").get_text()

                # Extract email address from sender string
                match = re.search(r"<(.*?)>", sender)
                sender_email = match.group(1) if match else sender

                print(f"--- New Email ---")
                print(f"From: {sender_email}")
                print(f"Subject: {subject}")
                print(f"Body: {body[:200]}...")  # Print a snippet of the body

                # Find the client ID in MongoDB using the sender's email
                client_id = get_client_id_by_email(sender_email)

                if client_id:
                    # Look for an existing conversation for this client
                    conversation_id = get_conversation_id_by_client_id(str(client_id))

                    # Append the email to the conversation, passing the ID if it exists
                    append_message_to_conversation(
                        client_id=str(client_id),
                        corps=body,
                        expediteur="client",
                        subject=subject,
                        conversation_id=(
                            str(conversation_id) if conversation_id else None
                        ),
                    )
                    update_conversation_status(str(conversation_id), "open")
                else:
                    print(f"❌ No client found for email: {sender_email}")

                # Mark the email as read
                service.users().messages().modify(
                    userId="me", id=msg_id, body={"removeLabelIds": ["UNREAD"]}
                ).execute()

    except HttpError as error:
        print(f"An API error occurred: {error}")


if __name__ == "__main__":
    gmail_service = get_gmail_service()
    if gmail_service:
        print("Starting email listener...")
        while True:
            # Check for new emails
            read_emails_last_24h(gmail_service)

            # Wait for 20 seconds before checking again
            print("Waiting for 20 seconds...")
            time.sleep(20)
