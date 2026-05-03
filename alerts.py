import os
import threading
import time
import cv2
import face_recognition as _fr
from datetime import datetime

import faces
import notifier
from config import COOLDOWN_SECONDS, DETECTIONS_DIR, FACE_TOLERANCE

_last_alert_time = 0.0
_lock = threading.Lock()
_session_intruders: list[dict] = []  # [{'path': str, 'encoding': ndarray|None, 'area': int}]

UNCONFIRMED_CONF_THRESHOLD = 0.8


def check(frame_rgb, frame_bgr, person_conf: float = 1.0) -> None:
    now = time.time()

    with _lock:
        in_cooldown = _last_alert_time > 0 and (now - _last_alert_time < COOLDOWN_SECONDS)

    if in_cooldown:
        _update_session(frame_rgb, frame_bgr)
        return

    if faces.has_whitelist():
        result = faces.is_known(frame_rgb)
        print(f"Face check: {result!r}  (True=known, False=unknown, None=no face found)")
        if result is True:
            return
        if result is None and person_conf < UNCONFIRMED_CONF_THRESHOLD:
            return

    _trigger(frame_bgr, frame_rgb, now)


def _trigger(frame_bgr, frame_rgb, now: float) -> None:
    global _last_alert_time, _session_intruders

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    path = os.path.join(DETECTIONS_DIR, f"intruder_{timestamp}.jpg")

    with _lock:
        if _last_alert_time > 0 and now - _last_alert_time < COOLDOWN_SECONDS:
            return
        _last_alert_time = now
        # Add placeholder immediately so concurrent _update_session threads
        # see a non-empty list before the slow _face_info call completes
        _session_intruders = [{'path': path, 'encoding': None, 'area': 0}]

    cv2.imwrite(path, frame_bgr)
    print(f"Intruder detected — saved {path}")

    encoding, area = _face_info(frame_rgb)
    if encoding is not None:
        with _lock:
            if _session_intruders and _session_intruders[0]['path'] == path:
                _session_intruders[0]['encoding'] = encoding
                _session_intruders[0]['area'] = area

    threading.Thread(target=notifier.send_alert, args=(path, timestamp), daemon=True).start()


def _update_session(frame_rgb, frame_bgr) -> None:
    if faces.has_whitelist():
        result = faces.is_known(frame_rgb)
        if result is True:
            return  # known person
        if result is None:
            return  # no face found, can't identify or improve

    encoding, area = _face_info(frame_rgb)
    if encoding is None:
        return  # no face to work with

    with _lock:
        idx = _match_intruder(encoding)
        if idx >= 0:
            stored = _session_intruders[idx]
            if _is_better(area, encoding, stored['area'], stored['encoding']):
                _replace_image(idx, frame_bgr, encoding, area)
        else:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            path = os.path.join(DETECTIONS_DIR, f"intruder_{timestamp}.jpg")
            cv2.imwrite(path, frame_bgr)
            _session_intruders.append({'path': path, 'encoding': encoding, 'area': area})
            print(f"New intruder in session — saved {path}")


def _replace_image(idx: int, frame_bgr, encoding, area: int) -> None:
    old_path = _session_intruders[idx]['path']
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    new_path = os.path.join(DETECTIONS_DIR, f"intruder_{timestamp}.jpg")
    cv2.imwrite(new_path, frame_bgr)
    try:
        os.remove(old_path)
    except OSError:
        pass
    _session_intruders[idx] = {'path': new_path, 'encoding': encoding, 'area': area}
    print(f"Improved intruder image: {new_path}")


def _match_intruder(encoding) -> int:
    # First: match by face encoding
    for i, intruder in enumerate(_session_intruders):
        if intruder['encoding'] is not None:
            if _fr.compare_faces([intruder['encoding']], encoding, tolerance=FACE_TOLERANCE)[0]:
                return i
    # Second: upgrade a no-face entry (first alert had no face detected)
    for i, intruder in enumerate(_session_intruders):
        if intruder['encoding'] is None:
            return i
    return -1


def _is_better(new_area: int, new_enc, old_area: int, old_enc) -> bool:
    if old_enc is None and new_enc is not None:
        return True  # now we have a face where we didn't before
    if new_enc is not None and old_enc is not None:
        return new_area > old_area  # bigger face = clearer image
    return False


def _face_info(frame_rgb) -> tuple:
    """Returns (encoding, area) of the first detectable face, or (None, 0)."""
    locations = _fr.face_locations(frame_rgb)
    locations = [l for l in locations if _sufficient(l)]
    if not locations:
        return None, 0
    encodings = _fr.face_encodings(frame_rgb, locations[:1])
    if not encodings:
        return None, 0
    top, right, bottom, left = locations[0]
    return encodings[0], (right - left) * (bottom - top)


def _sufficient(loc) -> bool:
    top, right, bottom, left = loc
    w, h = right - left, bottom - top
    return h > 0 and (w / h) >= 0.3 and (w * h) >= 2500


def last_alert_time() -> float:
    with _lock:
        return _last_alert_time


def detection_files() -> list[str]:
    return sorted(
        (f for f in os.listdir(DETECTIONS_DIR) if f.endswith(".jpg")),
        reverse=True,
    )
