#!/usr/bin/env python3
"""
InboxConverge
Fetches emails from POP3 mailboxes and forwards them to Gmail
"""

import os
import sys
import time
import poplib
import smtplib
import logging
import json
from email import parser
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from datetime import datetime
from typing import List, Dict, Optional
import schedule
from dotenv import load_dotenv
import ssl

# Load environment variables
load_dotenv()

# Configure logging
log_level = os.getenv('LOG_LEVEL', 'INFO')
logging.basicConfig(
    level=getattr(logging, log_level),
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)


class ThrottleManager:
    """Manages email sending throttling"""
    
    def __init__(self, emails_per_minute: int = 10):
        self.emails_per_minute = emails_per_minute
        self.send_times = []
    
    def wait_if_needed(self):
        """Wait if we've hit the throttle limit"""
        now = time.time()
        # Remove send times older than 1 minute
        self.send_times = [t for t in self.send_times if now - t < 60]
        
        if len(self.send_times) >= self.emails_per_minute:
            sleep_time = 60 - (now - self.send_times[0]) + 1
            if sleep_time > 0:
                logger.info(f"Throttling: sleeping for {sleep_time:.1f} seconds")
                time.sleep(sleep_time)
                self.send_times = []
        
        self.send_times.append(now)


class POP3Account:
    """Represents a POP3 account configuration"""
    
    def __init__(self, account_num: int):
        prefix = f"POP3_ACCOUNT_{account_num}_"
        self.host = os.getenv(f"{prefix}HOST")
        self.port = int(os.getenv(f"{prefix}PORT", "995"))
        self.user = os.getenv(f"{prefix}USER")
        self.password = os.getenv(f"{prefix}PASSWORD")
        self.use_ssl = os.getenv(f"{prefix}USE_SSL", "true").lower() == "true"
        self.account_num = account_num
    
    def is_valid(self) -> bool:
        """Check if account configuration is valid"""
        return bool(self.host and self.user and self.password)
    
    def __str__(self):
        return f"POP3Account({self.user}@{self.host})"


class EmailForwarder:
    """Main class for forwarding emails from POP3 to Gmail via InboxConverge"""
    
    def __init__(self):
        self.smtp_host = os.getenv('SMTP_HOST', 'smtp.gmail.com')
        self.smtp_port = int(os.getenv('SMTP_PORT', '587'))
        self.smtp_user = os.getenv('SMTP_USER')
        self.smtp_password = os.getenv('SMTP_PASSWORD')
        self.smtp_use_tls = os.getenv('SMTP_USE_TLS', 'true').lower() == 'true'
        self.gmail_destination = os.getenv('GMAIL_DESTINATION')
        self.max_emails_per_run = int(os.getenv('MAX_EMAILS_PER_RUN', '50'))
        self.throttle = ThrottleManager(
            int(os.getenv('THROTTLE_EMAILS_PER_MINUTE', '10'))
        )
        self.postmark_token = os.getenv('POSTMARK_API_TOKEN')
        self.postmark_from = os.getenv('POSTMARK_FROM_EMAIL')
        self.postmark_to = os.getenv('POSTMARK_TO_EMAIL')
        
        # Load POP3 accounts
        self.pop3_accounts = self._load_pop3_accounts()
        
    def _load_pop3_accounts(self) -> List[POP3Account]:
        """Load all configured POP3 accounts"""
        accounts = []
        for i in range(1, 100):  # Support up to 99 accounts
            account = POP3Account(i)
            if account.is_valid():
                accounts.append(account)
                logger.info(f"Loaded POP3 account: {account}")
            elif i == 1:
                # At least first account must be configured
                logger.error("No POP3 accounts configured!")
                break
            else:
                # No more accounts
                break
        return accounts
    
    def fetch_emails_from_pop3(self, account: POP3Account) -> List[bytes]:
        """Fetch emails from a POP3 account"""
        emails = []
        
        try:
            logger.info(f"Connecting to {account}")
            
            # Connect to POP3 server
            if account.use_ssl:
                pop_conn = poplib.POP3_SSL(account.host, account.port)
            else:
                pop_conn = poplib.POP3(account.host, account.port)
            
            # Login
            pop_conn.user(account.user)
            pop_conn.pass_(account.password)
            
            # Get message count
            num_messages = len(pop_conn.list()[1])
            logger.info(f"Found {num_messages} messages in {account}")
            
            # Fetch emails (limit to max_emails_per_run)
            for i in range(1, min(num_messages + 1, self.max_emails_per_run + 1)):
                try:
                    # Retrieve message
                    response, lines, octets = pop_conn.retr(i)
                    email_data = b'\r\n'.join(lines)
                    emails.append(email_data)
                    
                    # Delete from server after successful retrieval
                    pop_conn.dele(i)
                    logger.info(f"Retrieved and deleted message {i} from {account}")
                    
                except Exception as e:
                    logger.error(f"Error retrieving message {i} from {account}: {e}")
            
            pop_conn.quit()
            
        except Exception as e:
            logger.error(f"Error fetching from {account}: {e}")
            self.send_error_notification(f"POP3 fetch error from {account}", str(e))
        
        return emails
    
    def forward_email(self, email_data: bytes, source_account: str) -> bool:
        """Forward an email to Gmail"""
        try:
            # Parse the email
            msg = parser.BytesParser().parsebytes(email_data)
            
            # Create a new message for forwarding
            forward_msg = MIMEMultipart('mixed')
            forward_msg['From'] = self.smtp_user
            forward_msg['To'] = self.gmail_destination
            forward_msg['Date'] = formatdate(localtime=True)
            forward_msg['Message-ID'] = make_msgid()
            
            # Preserve original subject with prefix
            original_subject = msg.get('Subject', 'No Subject')
            forward_msg['Subject'] = f"[Fwd from {source_account}] {original_subject}"
            
            # Add original headers as reference
            header_info = f"Originally from: {msg.get('From', 'Unknown')}\n"
            header_info += f"Original Date: {msg.get('Date', 'Unknown')}\n"
            header_info += f"Original Subject: {original_subject}\n"
            header_info += f"Source POP3 Account: {source_account}\n"
            header_info += "-" * 50 + "\n\n"
            
            # Get the email body
            body = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
            else:
                body = msg.get_payload(decode=True).decode('utf-8', errors='ignore')
            
            # Combine header info and body
            full_body = header_info + body
            forward_msg.attach(MIMEText(full_body, 'plain', 'utf-8'))
            
            # Send via SMTP
            self.throttle.wait_if_needed()
            
            server = None
            try:
                if self.smtp_use_tls:
                    server = smtplib.SMTP(self.smtp_host, self.smtp_port)
                    server.starttls()
                else:
                    server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port)
                
                server.login(self.smtp_user, self.smtp_password)
                server.send_message(forward_msg)
                
                logger.info(f"Successfully forwarded email to {self.gmail_destination}")
                return True
            finally:
                if server:
                    try:
                        server.quit()
                    except Exception:
                        pass  # Ignore errors during cleanup
            
        except Exception as e:
            logger.error(f"Error forwarding email: {e}")
            self.send_error_notification("Email forwarding error", str(e))
            return False
    
    def send_error_notification(self, subject: str, error_message: str):
        """Send error notification via Postmarkapp"""
        if not self.postmark_token or not self.postmark_from or not self.postmark_to:
            logger.warning("Postmark not configured, skipping error notification")
            return
        
        try:
            import http.client
            
            conn = http.client.HTTPSConnection("api.postmarkapp.com")
            
            payload = json.dumps({
                "From": self.postmark_from,
                "To": self.postmark_to,
                "Subject": f"[InboxConverge Alert] {subject}",
                "TextBody": f"Error occurred at {datetime.now().isoformat()}\n\n{error_message}",
                "MessageStream": "outbound"
            })
            
            headers = {
                'Accept': 'application/json',
                'Content-Type': 'application/json',
                'X-Postmark-Server-Token': self.postmark_token
            }
            
            conn.request("POST", "/email", payload, headers)
            res = conn.getresponse()
            data = res.read()
            
            if res.status == 200:
                logger.info("Error notification sent via Postmark")
            else:
                logger.error(f"Failed to send Postmark notification: {data.decode('utf-8')}")
                
        except Exception as e:
            logger.error(f"Error sending Postmark notification: {e}")
    
    def process_all_accounts(self):
        """Process all configured POP3 accounts"""
        logger.info("=" * 60)
        logger.info("Starting email processing cycle")
        logger.info("=" * 60)
        
        total_forwarded = 0
        
        for account in self.pop3_accounts:
            try:
                emails = self.fetch_emails_from_pop3(account)
                logger.info(f"Fetched {len(emails)} emails from {account}")
                
                for email_data in emails:
                    if self.forward_email(email_data, str(account)):
                        total_forwarded += 1
                        
            except Exception as e:
                logger.error(f"Error processing account {account}: {e}")
                self.send_error_notification(f"Account processing error: {account}", str(e))
        
        logger.info(f"Processing cycle complete. Forwarded {total_forwarded} emails total.")
        logger.info("=" * 60)
    
    def validate_configuration(self) -> bool:
        """Validate that required configuration is present"""
        errors = []
        
        if not self.smtp_user:
            errors.append("SMTP_USER not configured")
        if not self.smtp_password:
            errors.append("SMTP_PASSWORD not configured")
        if not self.gmail_destination:
            errors.append("GMAIL_DESTINATION not configured")
        if not self.pop3_accounts:
            errors.append("No POP3 accounts configured")
        
        if errors:
            for error in errors:
                logger.error(f"Configuration error: {error}")
            return False
        
        logger.info("Configuration validated successfully")
        return True


def main():
    """Main entry point"""
    logger.info("InboxConverge starting...")
    
    forwarder = EmailForwarder()
    
    # Validate configuration
    if not forwarder.validate_configuration():
        logger.error("Configuration validation failed. Exiting.")
        sys.exit(1)
    
    # Get check interval
    check_interval = int(os.getenv('CHECK_INTERVAL_MINUTES', '5'))
    logger.info(f"Will check for new emails every {check_interval} minutes")
    
    # Run immediately on startup
    forwarder.process_all_accounts()
    
    # Schedule periodic checks
    schedule.every(check_interval).minutes.do(forwarder.process_all_accounts)
    
    # Main loop
    logger.info("Entering main scheduling loop...")
    while True:
        try:
            schedule.run_pending()
            time.sleep(1)
        except KeyboardInterrupt:
            logger.info("Received shutdown signal, exiting...")
            break
        except Exception as e:
            logger.error(f"Error in main loop: {e}")
            forwarder.send_error_notification("Main loop error", str(e))
            time.sleep(60)  # Wait a minute before retrying


if __name__ == "__main__":
    main()
