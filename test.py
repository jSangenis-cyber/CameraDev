from flask import Flask, Response
from picamera2 import Picamera2
from ultralytics import YOLO
import cv2
import os

app = Flask(__name__)

# --- Camera setup in RGB (what YOLO expects) ---
picam2 = Picamera2()
config = picam2.create_preview_configuration(
    main={"format": "RGB888", "size": (640, 480)}
)
picam2.configure(config)
picam2.start()

# --- Model setup ---
if not os.path.exists("yolov8n_ncnn_model"):
    print("Converting model to NCNN format (only happens once)...")
    temp = YOLO("yolov8n.pt")
    temp.export(format="ncnn")
    print("Conversion done!")

model = YOLO("yolov8n_ncnn_model")
print("Model loaded!")

# --- Frame generator ---
def generate():
    while True:
        # Capture RGB frame
        frame_rgb = picam2.capture_array()

        # Run YOLO (accepts RGB)
        results = model(frame_rgb, verbose=False)

        # .plot() already returns BGR — no conversion needed
        annotated_bgr = results[0].plot()

        # Encode directly as JPEG (OpenCV needs BGR — already is)
        ret, buffer = cv2.imencode('.jpg', annotated_bgr,
                                   [cv2.IMWRITE_JPEG_QUALITY, 80])
        if not ret:
            continue

        yield (b'--frame\r\n'
               b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

# --- Routes ---
@app.route('/')
def index():
    return '''
    <html>
    <head>
        <title>YOLO Detection</title>
        <style>
            * { box-sizing: border-box; margin: 0; padding: 0; }
            body {
                background: #111;
                display: flex;
                flex-direction: column;
                align-items: center;
                justify-content: center;
                min-height: 100vh;
                font-family: sans-serif;
                padding: 20px;
            }
            h1 {
                color: #fff;
                font-size: 20px;
                margin-bottom: 16px;
            }
            .badge {
                background: #222;
                color: #0f0;
                font-size: 12px;
                padding: 4px 12px;
                border-radius: 20px;
                margin-bottom: 16px;
            }
            .stream-container {
                width: 100%;
                max-width: 640px;
            }
            .stream-container img {
                display: block;
                width: 100%;
                height: auto;
                border: 2px solid #333;
                border-radius: 8px;
            }
            .footer {
                color: #555;
                font-size: 12px;
                margin-top: 12px;
            }
        </style>
    </head>
    <body>
        <h1>YOLO Live Detection</h1>
        <div class="badge">LIVE</div>
        <div class="stream-container">
            <img src="/stream" width="640" height="480" />
        </div>
        <p class="footer">YOLOv8n NCNN — Raspberry Pi 5</p>
    </body>
    </html>
    '''

@app.route('/stream')
def stream():
    return Response(generate(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

app.run(host='0.0.0.0', port=8080, threaded=True)
