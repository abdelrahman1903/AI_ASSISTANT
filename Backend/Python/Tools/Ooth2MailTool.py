import base64
import json
import requests
from datetime import datetime, timedelta, timezone
from dotenv import load_dotenv
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import re
from bs4 import BeautifulSoup
from dateutil.parser import isoparse  # safer ISO parser

load_dotenv()

CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID")
CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET")
TOKEN_URI = os.getenv("GOOGLE_TOKEN_URI", "https://oauth2.googleapis.com/token")

class MailToolOAuth:
    def __init__(self, access_token: str, refresh_token: str, token_expiry: str, Bearer_TOKEN: str):
        """
        Initialize Gmail OAuth mail tool.
        access_token: current google access token
        refresh_token: long-lived refresh token
        token_expiry: ISO timestamp when access token expires
        """
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.token_expiry = token_expiry
        self.Bearer_TOKEN = Bearer_TOKEN  # Placeholder for Bearer token if needed

    # -------------------------------------------------------
    # 🔁 AUTO REFRESH TOKEN
    # -------------------------------------------------------
    def refresh_google_token(self, refresh_token: str):
        try:
            data = {
                "client_id": CLIENT_ID,
                "client_secret": CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            }

            response = requests.post(TOKEN_URI, data=data)
            response.raise_for_status()

            token_data = response.json()

            new_access_token = token_data["access_token"]
            expires_in = token_data.get("expires_in", 3600)

            # ALWAYS CREATE TZ-AWARE EXPIRY
            expiry_time = datetime.now(timezone.utc) + timedelta(seconds=expires_in)
            if expiry_time.tzinfo is None:
                expiry_time = expiry_time.replace(tzinfo=timezone.utc)
            else:
                expiry_time = expiry_time.astimezone(timezone.utc)

            # 🔁 Save to Node.js backend
            url = f"http://localhost:5000/api/v1/fastapi/setUserOAuthInfo"
            headers = {
                "Content-Type": "application/json",
                "Authorization": self.Bearer_TOKEN
            }
            payload = {
                "access_token": new_access_token,
                "refresh_token": refresh_token,
                "access_token_expiry": expiry_time.isoformat(),
                "is_authenticated": True
            }
            backend_response = requests.post(url, headers=headers, json=payload)
            if backend_response.status_code == 200:
                print("✅ User OAuth info set successfully in Node.js backend.")
            else:
                print("❌ Failed to set User OAuth info in Node.js backend:", backend_response.text)

            return {
                "access_token": new_access_token,
                "expiry": expiry_time.isoformat()
            }

        except Exception as e:
            print(f"❌ Error refreshing token: {e}")
            return None
    
    def ensure_access_token(self):
        # expiry_time = datetime.fromisoformat(self.token_expiry)
        # now = datetime.now(timezone.utc)
        expiry_time = isoparse(self.token_expiry)  # parses ISO with tz correctly
        now = datetime.now(timezone.utc)
        print(f"Current time: {now}, Token expiry: {expiry_time}",flush=True)

        # Refresh if token expired or close to expiry
        if now >= expiry_time:
            print("🔄 Access token expired — refreshing...")

            new_token = self.refresh_google_token(self.refresh_token)
            if not new_token:
                return False

            self.access_token = new_token["access_token"]
            self.token_expiry = new_token["expiry"]

            print("🔄 Token refreshed successfully")

        return True

    # -------------------------------------------------------
    # ✉️ SEND EMAIL THROUGH GMAIL API
    # -------------------------------------------------------
    def send_email(self, sender_email: str, to_email: str, subject: str, body: str):
        if not self.ensure_access_token():
            return "❌ Failed to refresh token. Cannot send email."

        try:
            print("DEBUG TYPES:", type(sender_email), type(to_email), type(subject))
            print("DEBUG VALUES:", sender_email, to_email, subject)
            # Create MIME message
            message = MIMEMultipart()
            message["from"] = sender_email
            message["to"] = to_email
            message["subject"] = subject
            message.attach(MIMEText(body, "plain"))

            # Encode to base64
            raw_message = base64.urlsafe_b64encode(
                message.as_bytes()
            ).decode()

            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"
            headers = {"Authorization": f"Bearer {self.access_token}",
                       "Content-Type": "application/json"}

            payload = {"raw": raw_message}

            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                return f"✅ Email sent to {to_email}"

            print(response.text)
            return f"❌ Failed to send email: {response.text}"

        except Exception as e:
            print("❌ Error:", e)
            return "❌ Error sending email"

    # -------------------------------------------------------
    # 📥 READ UNREAD EMAILS FROM GMAIL API
    # -------------------------------------------------------
    def fetch_unread_emails(self, max_count=10):
        """
        Fetch unread emails and return them as ONE clean string.
        """
        if not self.ensure_access_token():
            return "❌ Failed to refresh token. Cannot read emails."

        try:
            # Search unread messages
            url = "https://gmail.googleapis.com/gmail/v1/users/me/messages"
            params = {
                "q": "is:unread",
                "maxResults": max_count
            }
            headers = {"Authorization": f"Bearer {self.access_token}"}

            search_response = requests.get(
                url, headers=headers, params=params
            ).json()

            if "messages" not in search_response:
                return "📭 No unread emails."

            raw_messages = []

            # Fetch each unread email
            for msg in search_response["messages"]:
                msg_id = msg["id"]
                msg_url = f"https://gmail.googleapis.com/gmail/v1/users/me/messages/{msg_id}"
                msg_data = requests.get(msg_url, headers=headers).json()

                raw_messages.append(msg_data)

            return parse_all_emails_as_string(raw_messages)

        except Exception as e:
            print("❌ Error:", e)
            return []

    # def parse_email(self, msg_data):
    #     headers = msg_data["payload"]["headers"]

    #     def get_header(name):
    #         for h in headers:
    #             if h["name"].lower() == name.lower():
    #                 return h["value"]
    #         return ""

    #     subject = get_header("Subject")
    #     sender = get_header("From")
    #     date = get_header("Date")

    #     body = ""
    #     parts = msg_data["payload"].get("parts", [])

    #     for part in parts:
    #         if part["mimeType"] == "text/plain":
    #             data = part["body"]["data"]
    #             body = base64.urlsafe_b64decode(data).decode()
    #             break

    #     return {
    #         "from": sender,
    #         "subject": subject,
    #         "date": date,
    #         "body": body
    #     }


def extract_body(payload):
    """
    Recursively extract text/plain or text/html body.
    """
    if "parts" in payload:
        for part in payload["parts"]:
            result = extract_body(part)
            if result:
                return result

    mime_type = payload.get("mimeType", "")
    body_data = payload.get("body", {}).get("data", "")

    if not body_data:
        return ""

    decoded = base64.urlsafe_b64decode(body_data).decode(errors="ignore")

    # Prefer text/plain
    if mime_type == "text/plain":
        return decoded

    # If HTML, clean it
    if mime_type == "text/html":
        soup = BeautifulSoup(decoded, "html.parser")
        return soup.get_text(separator="\n")

    return ""
    
    # # -------------------------------------------------------------------
    # # 📨 Helper to parse Gmail API email payload to one single string
    # # -------------------------------------------------------------------
def parse_all_emails_as_string(messages):
    """
    Takes a list of Gmail messages (full payloads)
    and returns a single clean string.
    """
    output = []

    for msg_data in messages:
        headers = msg_data["payload"]["headers"]

        def get_header(name):
            for h in headers:
                if h["name"].lower() == name.lower():
                    return h["value"]
            return ""

        sender = get_header("From")
        subject = get_header("Subject")
        date = get_header("Date")

        body = extract_body(msg_data["payload"])
        if not body.strip():
            body = "(No body)"

        # Remove repeated whitespace
        body = re.sub(r"\n\s*\n", "\n\n", body).strip()

        # Build the combined email text
        email_text = (
            f"From: {sender}\n"
            f"Subject: {subject}\n"
            f"Date: {date}\n\n"
            f"{body}\n"
            f"=============================="
        )

        output.append(email_text)

    # Join all emails into one string
    return "\n".join(output)


