import os
from dotenv import load_dotenv

load_dotenv()

GMAIL_USER         = os.getenv("GMAIL_USER")
GMAIL_APP_PASSWORD = os.getenv("GMAIL_APP_PASSWORD")
ALERT_EMAIL        = os.getenv("ALERT_EMAIL", GMAIL_USER)
COOLDOWN_SECONDS   = int(os.getenv("COOLDOWN_SECONDS", "300"))

KNOWN_FACES_DIR = "known_faces"
DETECTIONS_DIR  = "detections"
FACE_TOLERANCE  = 0.6   # lower = stricter match
CHECK_INTERVAL  = 2     # seconds between face-recognition runs

IDLE_FPS   = float(os.getenv("IDLE_FPS",   "5"))   # FPS when no person in frame
ACTIVE_FPS = float(os.getenv("ACTIVE_FPS", "15"))  # FPS when person detected
