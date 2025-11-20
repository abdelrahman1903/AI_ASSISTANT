# from google import genai
# from google.genai import types
import smtplib
import imapclient
import email
from email.header import decode_header
from email.message import EmailMessage
from email import policy
from typing import Literal, Dict
from pydantic import BaseModel, Field
import os
from dotenv import load_dotenv
import json
import re
from email_validator import validate_email, EmailNotValidError
# from datetime import datetime, timedelta

load_dotenv()
api_key = os.getenv("LLM_API_KEY")



# class EmailRequest(BaseModel):
#     """extract email components from the user message."""

# class EmailRequest(BaseModel):
#     """Extract the components needed to send an email from the user's message."""

#     subject: str = Field(
#         description=(
#             "The subject line of the email. If not explicitly stated by the user, "
#             "infer an appropriate subject based on the context of the message."
#         )
#     )
#     body: str = Field(
#         description=(
#             "The main content of the email. This may not always be explicitly mentioned — for example, "
#             "the user might say: 'Send a congratulations mail to example@example.com for his graduation'. "
#             "In such cases, infer the full body and format it clearly, using appropriate spacing and line breaks."
#         )
#     )
#     to_email: str = Field(
#         description="The recipient’s email address extracted from the user's message."
#     )


def is_valid_email(email: str) -> bool:
    try:
        # Validate and normalize the email
        valid = validate_email(email)
        # print("Normalized email:", valid.email)  # If you want to use the normalized version
        return True
    except EmailNotValidError as e:
        print("Invalid email:", str(e))
        return False

def send_email(
    subject: str,
    body: str,
    to_email: str,
    from_email: str,
    from_email_type: str,
    smtp_username: str,
    smtp_password: str,
    # smtp_server: str,
    # smtp_port: int,
    # is_html: bool = False
):
    try:

        # Validate recipient email
        if not is_valid_email(to_email):
            return f"❌ Invalid recipient email address: {to_email}"

        # Validate subject and body
        if not subject.strip():
            return "❌ Email subject cannot be empty."
        if not body.strip():
            return "❌ Email body cannot be empty."
        
        from_email_type = from_email_type.strip().lower()
        if from_email_type == "gmail" :
            smtp_server = "smtp.gmail.com"
            smtp_port = 465
            # use_ssl = True
        # elif from_email_type == "outlook" or from_email_type.lower() == "hotmail":
        #     smtp_server = "smtp.office365.com"
        #     smtp_port = 587
        #     use_ssl = False  # Outlook uses STARTTLS
        elif from_email_type == "yahoo" :
            smtp_server = "smtp.mail.yahoo.com"
            smtp_port = 465
            # use_ssl = True
        else:
            return f"Sorry {from_email_type} email type is unsupported, the system currently only supports Gmail, Outlook, Hotmail, and yahoo"
        # Create email message
        msg = EmailMessage()
        msg["Subject"] = subject
        msg["From"] = from_email
        msg["To"] = to_email
        msg.set_content(body, subtype="plain")
        # Connect to SMTP server and send
        # Connect and send
        # if use_ssl:
        with smtplib.SMTP_SSL(smtp_server, smtp_port) as smtp:
            smtp.login(smtp_username, smtp_password)
            smtp.send_message(msg)
        # else:
        #     with smtplib.SMTP(smtp_server, smtp_port) as smtp:
        #         print("3")
        #         smtp.ehlo()
        #         smtp.starttls()
        #         smtp.ehlo()
        #         smtp.set_debuglevel(1)
        #         smtp.login(smtp_username, smtp_password)
        #         print("4")
        #         smtp.send_message(msg)
        #         print("5")
        print(f"✅ Email sent to {to_email}")
        return f"✅ Email sent to {to_email}"

    except Exception as e:
        print(f"❌ Error sending email: {e}")
        return f"❌ Error sending email, please try again"

def get_email_provider(email: str) -> str:
    try:
        domain = email.split("@")[1]           # e.g. gmail.com
        provider = domain.split(".")[0]        # e.g. gmail
        return provider.lower()
    except IndexError:
        raise ValueError("Invalid email format. Cannot extract provider.")


class MailTool:
    if not api_key:
        raise ValueError("Missing LLM_API_KEY. Did you forget to set it in your .env file?")
    def __init__(self):
        # self.LLMmodel = genai.Client(api_key=api_key)
        # genai.configure(api_key=api_key)
        # self.LLMmodel = genai.GenerativeModel(
        #     model_name="models/gemini-2.5-flash",
        # )
        
        self.sender_email = os.getenv("from_email")
        self.email_password = os.getenv("smtp_password")

    def send_email_tool(self,to_email,subject,body) -> dict: #userInput
        try:
            from_email_type = get_email_provider(str(self.sender_email))
            # messages=[
            #     {"role": "user", "parts": [userInput]},
            # ]
            # city_name_response = self.LLMmodel.generate_content(
            #     messages,
            #     generation_config={
            #         "response_mime_type": "application/json",
            #         "response_schema": EmailRequest
            #     }
            # )
            # temp = json.loads(city_name_response.text)
            # print(f"",temp)
            # subject = temp.get("subject")
            # print(f"",subject)
            # body = temp.get("body")
            # print(f"",body)
            # to_email = temp.get("to_email")
            # print(f"",to_email)
            return send_email(subject,body,to_email,self.sender_email,from_email_type,self.sender_email,self.email_password)
        except Exception as e:
            print(f"❌ Error sending email: {e}")
            return "❌ Error sending email, please try again"
        
    # ⚠️⚠️ there should be a loop in the frontend that prints all unread emails as the function returns a list of emails
    def fetch_unread_emails(
        self,
        # email_address: str,
        # password: str,
        max_count: int = 10
    ):
        imap_server: str = "imap.gmail.com"
        emails = []  # collect all emails to return
        with imapclient.IMAPClient(imap_server, ssl=True) as client:
            client.login(self.sender_email, self.email_password)
            client.select_folder("INBOX", readonly=True)

            # Search for unread emails
            uids = client.search(['UNSEEN'])
            uids = sorted(uids, reverse=True)[:max_count]  # limit to latest N unread emails

            # # 3 days ago from today
            # three_days_ago = datetime.now() - timedelta(days=3)
            # date_str = three_days_ago.strftime('%d-%b-%Y')  # IMAP expects format like "04-Jul-2025"

            # uids = client.search(['UNSEEN', 'SINCE', date_str])
            # uids = sorted(uids, reverse=True)  # Sort newest first

            for uid in uids:
                raw_message = client.fetch([uid], ['BODY[]'])[uid][b'BODY[]']
                msg = email.message_from_bytes(raw_message, policy=policy.default)

                # Extract header fields
                subject, encoding = decode_header(msg["Subject"])[0]
                if isinstance(subject, bytes):
                    subject = subject.decode(encoding or "utf-8", errors="ignore")

                from_ = msg.get("From")
                date = msg.get("Date")

                # Extract body (preferring plain text part)
                if msg.is_multipart():
                    for part in msg.walk():
                        if part.get_content_type() == "text/plain" and not part.get("Content-Disposition"):
                            body = part.get_content()
                            break
                    else:
                        body = "[No plain text part found]"
                else:
                    body = msg.get_content()

                print("📩 --- New Email ---")
                print(f"From: {from_}")
                print(f"Date: {date}")
                print(f"Subject: {subject}")
                print("Body:")
                print(body)
                print("\n" + "="*50 + "\n")

                emails.append({
                    "from": from_,
                    "date": date,
                    "subject": subject,
                    "body": body
                })
            print(emails)
            return emails

# MailTool().fetch_unread_emails(10)

# userInput = input("Ask your mail-related task:")   
# print(send_email_tool(userInput))

