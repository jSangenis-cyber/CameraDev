import os
from config import KNOWN_FACES_DIR, DETECTIONS_DIR
import faces
import camera
from web import app

os.makedirs(KNOWN_FACES_DIR, exist_ok=True)
os.makedirs(DETECTIONS_DIR,  exist_ok=True)

faces.load()
camera.start()

app.run(host="0.0.0.0", port=8080, threaded=True)
