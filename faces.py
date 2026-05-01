import os
import face_recognition
from config import KNOWN_FACES_DIR, FACE_TOLERANCE

_encodings: list = []
_names:     list = []


def load():
    global _encodings, _names
    encodings, names = [], []
    for fn in sorted(os.listdir(KNOWN_FACES_DIR)):
        if not fn.lower().endswith((".jpg", ".jpeg", ".png")):
            continue
        name  = os.path.splitext(fn)[0]
        image = face_recognition.load_image_file(os.path.join(KNOWN_FACES_DIR, fn))
        encs  = face_recognition.face_encodings(image)
        if encs:
            encodings.append(encs[0])
            names.append(name)
            print(f"  Loaded face: {name}")
        else:
            print(f"  Warning: no face detected in {fn}, skipping")
    _encodings, _names = encodings, names
    print(f"Known faces: {len(_encodings)}")
    if not _encodings:
        print("  No known faces — will alert on ANY person detected.")


def has_whitelist() -> bool:
    return bool(_encodings)


def is_known(frame_rgb) -> bool | None:
    """
    Returns True  if a recognised face is found in the frame.
    Returns False if an unrecognised face is found.
    Returns None  if no face is detected at all (e.g. person seen from behind).
    """
    locations = face_recognition.face_locations(frame_rgb)
    if not locations:
        return None
    for enc in face_recognition.face_encodings(frame_rgb, locations):
        if any(face_recognition.compare_faces(_encodings, enc, tolerance=FACE_TOLERANCE)):
            return True
    return False


def known_filenames() -> list[str]:
    return sorted(
        f for f in os.listdir(KNOWN_FACES_DIR)
        if f.lower().endswith((".jpg", ".jpeg", ".png"))
    )
