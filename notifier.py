import os
import smtplib
from email.mime.image import MIMEImage
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import GMAIL_USER, GMAIL_APP_PASSWORD, ALERT_EMAIL


def send_alert(image_path: str, timestamp: str) -> None:
    if not GMAIL_USER or not GMAIL_APP_PASSWORD:
        print("Email not configured (.env missing) — skipping alert.")
        return
    try:
        msg = MIMEMultipart()
        msg["From"]    = GMAIL_USER
        msg["To"]      = ALERT_EMAIL
        msg["Subject"] = f"Intruder detected — {timestamp}"
        msg.attach(MIMEText(
            f"Unknown person detected at {timestamp}.\nSee attached photo.", "plain"
        ))
        with open(image_path, "rb") as f:
            msg.attach(MIMEImage(f.read(), name=os.path.basename(image_path)))
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            server.login(GMAIL_USER, GMAIL_APP_PASSWORD)
            server.sendmail(GMAIL_USER, ALERT_EMAIL, msg.as_string())
        print(f"Alert email sent — {timestamp}")
    except Exception as e:
        print(f"Email error: {e}")
