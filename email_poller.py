import imaplib
import email
import requests
import time
import os
from email.header import decode_header

IMAP_SERVER = os.environ.get("IMAP_SERVER", "imap.gmail.com")
EMAIL_ACCOUNT = os.environ.get("EMAIL_ACCOUNT", "yourcompany.inout@gmail.com")
EMAIL_PASSWORD = os.environ.get("EMAIL_PASSWORD", "app_password_here")
API_URL = "http://localhost:8000/api/update_message"

def process_emails():
    try:
        # Connect to server
        mail = imaplib.IMAP4_SSL(IMAP_SERVER)
        mail.login(EMAIL_ACCOUNT, EMAIL_PASSWORD)
        
        # Select mailbox
        mail.select("inbox")
        
        # Search for unread emails
        status, messages = mail.search(None, "UNSEEN")
        if status != "OK":
            print("Failed to search emails")
            return
            
        email_ids = messages[0].split()
        if not email_ids:
            pass # No new emails
            
        for eid in email_ids:
            # Fetch email
            res, msg_data = mail.fetch(eid, "(RFC822)")
            for response_part in msg_data:
                if isinstance(response_part, tuple):
                    msg = email.message_from_bytes(response_part[1])
                    
                    # Extract subject
                    subject_header = msg.get("Subject", "")
                    if subject_header:
                        subject, encoding = decode_header(subject_header)[0]
                        if isinstance(subject, bytes):
                            subject = subject.decode(encoding if encoding else "utf-8", errors="ignore")
                    else:
                        subject = "Unavailable"
                        
                    # Extract sender
                    from_ = msg.get("From", "")
                    sender_email = from_.split("<")[-1].strip(">").strip()
                    
                    print(f"Processing email from {sender_email} with subject: {subject}")
                    
                    # Use the Subject as the custom message
                    custom_msg = subject.strip()
                    
                    try:
                        resp = requests.post(API_URL, json={
                            "email": sender_email,
                            "message": custom_msg
                        })
                        if resp.status_code == 200:
                            print(f"Successfully updated status for {sender_email}")
                        else:
                            print(f"Failed to update API for {sender_email}: {resp.text}")
                    except Exception as e:
                        print(f"Error calling API: {e}")
                        
            # Mark as read
            mail.store(eid, '+FLAGS', '\\Seen')
            
        mail.logout()
    except Exception as e:
        print(f"IMAP Error: {e}")

if __name__ == "__main__":
    print(f"Starting Email Poller (Polling {IMAP_SERVER} as {EMAIL_ACCOUNT})...")
    while True:
        process_emails()
        time.sleep(60) # Poll every 60 seconds
