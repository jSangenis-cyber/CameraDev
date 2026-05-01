# CLAUDE.md

This file provides guidance to Claude Code when working with code in this repository.

## Running the Application

```bash
source ai_env/bin/activate
python main.py
```

The Flask server starts on `http://0.0.0.0:8080`.

## File Structure

```
main.py       — entry point: wires everything together, starts Flask
config.py     — all settings loaded from .env
faces.py      — loads known faces from known_faces/, checks if a face is recognised
alerts.py     — intruder detection logic, cooldown, saves photos, triggers email
notifier.py   — sends alert email via Gmail SMTP
camera.py     — Picamera2 capture loop + YOLO inference (background thread)
web.py        — Flask routes (/, /stream, /admin, static file serving)

known_faces/  — put <name>.jpg photos here to whitelist people (gitignored)
detections/   — intruder photos saved here automatically (gitignored)
.env          — credentials (gitignored, see .env.example)
```

## Architecture

**Pipeline:**
1. `camera.py` captures RGB888 frames at 640×480 via Picamera2
2. YOLOv8n NCNN runs inference on each frame
3. When a `person` is detected, a background thread runs face recognition every 5 s
4. `faces.py` compares against encodings loaded from `known_faces/`
5. Unknown person → `alerts.py` saves a JPEG to `detections/` and emails it
6. `results[0].plot()` returns annotated BGR; encoded as JPEG and streamed as MJPEG

**Routes:**
- `/`            — live stream page
- `/stream`      — MJPEG multipart stream
- `/admin`       — dashboard: known people + recent detections
- `/known_faces/<file>` — serves face photos
- `/detections/<file>`  — serves intruder photos

## Model

- Source: `yolov8n.pt` (PyTorch, conversion only)
- Runtime: `yolov8n_ncnn_model/` (NCNN, edge-optimised, auto-created on first run)
- Detects 80 COCO classes; only `person` triggers the alert pipeline

## Color Space

Picamera2 outputs RGB888. YOLO accepts RGB. `results[0].plot()` returns BGR.
`cv2.imencode` expects BGR. No conversion needed between capture and stream.
Face recognition (`face_recognition` library) also expects RGB — pass `frame_rgb` directly.

## Dependencies

Key packages in `ai_env/` (no requirements.txt):
- `flask`
- `picamera2`
- `ultralytics` (YOLOv8)
- `opencv-python`
- `face_recognition` (dlib-based, install once: `pip install face_recognition`)
- `python-dotenv` (`pip install python-dotenv`)

The venv uses `system-site-packages = true` for Pi-specific libs (libcamera, etc.).

## Hardware

Raspberry Pi 5. NCNN format chosen for CPU performance on ARM.
Avoid dependencies requiring GPU or unavailable as ARM wheels.

## Configuration (.env)

```
GMAIL_USER=you@gmail.com
GMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx   # Gmail App Password, not your login password
ALERT_EMAIL=you@gmail.com                # defaults to GMAIL_USER if omitted
COOLDOWN_SECONDS=300                     # seconds between alert emails (default 5 min)
```

## Known Faces

Drop a clear frontal photo named `<person>.jpg` into `known_faces/`.
Restart the app to reload. If the folder is empty, the system alerts on **any** person.
