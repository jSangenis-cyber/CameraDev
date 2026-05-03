import os
import threading
import time

import cv2
from picamera2 import Picamera2
from ultralytics import YOLO

import alerts
from config import CHECK_INTERVAL, IDLE_FPS, ACTIVE_FPS

_frame:      bytes | None = None
_frame_lock  = threading.Lock()
_check_spawned = 0.0  # only written from the single capture thread


def _setup_model() -> YOLO:
    if not os.path.exists("yolov8n_ncnn_model"):
        print("Converting model to NCNN (one-time, ~1 min)...")
        YOLO("yolov8n.pt").export(format="ncnn")
    model = YOLO("yolov8n_ncnn_model")
    print("Model loaded.")
    return model


def _setup_camera() -> Picamera2:
    cam = Picamera2()
    cam.configure(cam.create_preview_configuration(
        main={"format": "RGB888", "size": (640, 480)}
    ))
    cam.start()
    return cam


def _capture_loop(cam: Picamera2, model: YOLO) -> None:
    global _frame, _check_spawned
    while True:
        t_start = time.time()

        frame_rgb     = cam.capture_array()
        results       = model(frame_rgb, verbose=False)
        annotated_bgr = results[0].plot()

        person_conf = max(
            (float(b.conf[0]) for b in results[0].boxes
             if results[0].names[int(b.cls[0])] == "person"),
            default=0.0,
        )
        person_seen = person_conf > 0.0

        now = time.time()
        if person_seen and now - _check_spawned > CHECK_INTERVAL:
            _check_spawned = now
            threading.Thread(
                target=alerts.check,
                args=(frame_rgb.copy(), annotated_bgr.copy(), person_conf),
                daemon=True,
            ).start()

        ret, buf = cv2.imencode(".jpg", annotated_bgr, [cv2.IMWRITE_JPEG_QUALITY, 80])
        if ret:
            with _frame_lock:
                _frame = buf.tobytes()

        target_fps = ACTIVE_FPS if person_seen else IDLE_FPS
        elapsed = time.time() - t_start
        sleep_time = (1.0 / target_fps) - elapsed
        if sleep_time > 0:
            time.sleep(sleep_time)


def start() -> None:
    cam   = _setup_camera()
    model = _setup_model()
    threading.Thread(target=_capture_loop, args=(cam, model), daemon=True).start()


def latest_frame() -> bytes | None:
    with _frame_lock:
        return _frame


def stream():
    """MJPEG generator for Flask."""
    while True:
        frame = latest_frame()
        if frame is None:
            time.sleep(0.05)
            continue
        yield (b"--frame\r\n"
               b"Content-Type: image/jpeg\r\n\r\n" + frame + b"\r\n")
        time.sleep(0.033)
