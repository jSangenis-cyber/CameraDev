import os
import threading
import time
import cv2
from datetime import datetime

import faces
import notifier
from config import COOLDOWN_SECONDS, DETECTIONS_DIR

_last_alert_time = 0.0
_lock = threading.Lock()


def check(frame_rgb) -> None:
    """
    Called from a background thread when YOLO sees a person.
    Runs face recognition; if an intruder is found and cooldown has passed,
    saves a photo and sends an email alert.
    """
    now = time.time()

    with _lock:
        if now - _last_alert_time < COOLDOWN_SECONDS:
            return  # still in cooldown, skip expensive face check

    if faces.has_whitelist():
        result = faces.is_known(frame_rgb)
        print(f"Face check: {result!r}  (True=known, False=unknown, None=no face found)")
        if result is True:
            return  # known person
        if result is None:
            return  # person detected but no face visible — don't false-alert
        # result is False → unknown face
    # else: no whitelist configured → alert on any person

    _trigger(frame_rgb, now)


def _trigger(frame_rgb, now: float) -> None:
    global _last_alert_time
    with _lock:
        if now - _last_alert_time < COOLDOWN_SECONDS:
            return  # another thread beat us here
        _last_alert_time = now

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path      = os.path.join(DETECTIONS_DIR, f"intruder_{timestamp}.jpg")
    cv2.imwrite(path, cv2.cvtColor(frame_rgb, cv2.COLOR_RGB2BGR))
    print(f"Intruder detected — saved {path}")

    threading.Thread(target=notifier.send_alert, args=(path, timestamp), daemon=True).start()


def last_alert_time() -> float:
    with _lock:
        return _last_alert_time


def detection_files() -> list[str]:
    return sorted(
        (f for f in os.listdir(DETECTIONS_DIR) if f.endswith(".jpg")),
        reverse=True,
    )
