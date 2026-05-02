import os
import time
from datetime import datetime

from flask import Flask, Response, jsonify, send_from_directory

import alerts
import camera
import faces
from config import COOLDOWN_SECONDS, DETECTIONS_DIR, KNOWN_FACES_DIR

app = Flask(__name__)


@app.route("/")
def index():
    return """
    <html><head>
    <title>Home Security</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      * { box-sizing: border-box; margin: 0; padding: 0; }
      body { background: #111; display: flex; flex-direction: column;
             align-items: center; justify-content: center;
             min-height: 100vh; font-family: sans-serif; padding: 20px; }
      h1   { color: #fff; font-size: 20px; margin-bottom: 12px; }
      .badge { background: #222; color: #0f0; font-size: 12px;
               padding: 4px 12px; border-radius: 20px; margin-bottom: 16px; }
      .stream-container { width: 100%; max-width: 640px; }
      .stream-container img { display: block; width: 100%; height: auto;
                              border: 2px solid #333; border-radius: 8px; }
      .footer { color: #555; font-size: 12px; margin-top: 12px; }
      .footer a { color: #0af; text-decoration: none; }
    </style>
    </head><body>
    <h1>Home Security Camera</h1>
    <div class="badge">LIVE</div>
    <div class="stream-container"><img src="/stream"></div>
    <p class="footer">YOLOv8n NCNN &mdash; <a href="/admin">Admin</a></p>
    </body></html>
    """


@app.route("/stream")
def stream():
    return Response(camera.stream(), mimetype="multipart/x-mixed-replace; boundary=frame")


@app.route("/admin")
def admin():
    known      = faces.known_filenames()
    detections = alerts.detection_files()[:20]

    alert_ts   = alerts.last_alert_time()
    last_alert = (
        datetime.fromtimestamp(alert_ts).strftime("%Y-%m-%d %H:%M:%S")
        if alert_ts else "Never"
    )
    total = len(alerts.detection_files())

    known_html = "".join(
        f'<div class="card"><img src="/known_faces/{f}" loading="lazy">'
        f'<p>{os.path.splitext(f)[0]}</p></div>'
        for f in known
    ) or '<p class="empty">No known faces — add photos to <code>known_faces/</code>.</p>'

    det_html = "".join(
        f'<div class="card"><a href="/detections/{f}" target="_blank">'
        f'<img src="/detections/{f}" loading="lazy"></a>'
        f'<p>{f[9:-4]}</p></div>'
        for f in detections
    ) or '<p class="empty">No detections yet.</p>'

    return f"""
    <html><head>
    <title>Security Dashboard</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <style>
      * {{ box-sizing: border-box; margin: 0; padding: 0; }}
      body {{ background: #111; color: #fff; font-family: sans-serif;
              padding: 24px; max-width: 1000px; margin: 0 auto; }}
      h1   {{ font-size: 22px; margin-bottom: 20px; }}
      h2   {{ font-size: 12px; color: #555; margin: 28px 0 12px;
              text-transform: uppercase; letter-spacing: 1px; }}
      nav  {{ margin-bottom: 20px; }}
      nav a {{ color: #0af; text-decoration: none; font-size: 14px; }}
      .status {{ background: #1a1a1a; border-radius: 8px; padding: 16px;
                 display: flex; gap: 28px; flex-wrap: wrap; }}
      .stat  {{ font-size: 14px; color: #666; }}
      .stat span {{ color: #0f0; font-weight: bold; }}
      .grid  {{ display: grid;
                grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
                gap: 12px; }}
      .card  {{ background: #1a1a1a; border-radius: 8px; overflow: hidden;
                text-align: center; }}
      .card img {{ width: 100%; height: 160px; object-fit: cover; display: block; }}
      .card p   {{ padding: 8px; font-size: 11px; color: #888;
                   word-break: break-all; }}
      .empty {{ color: #555; font-size: 14px; padding: 8px 0; }}
      code   {{ background: #222; padding: 2px 6px; border-radius: 4px;
                font-size: 12px; }}
      .cooldown-active span {{ color: #f80 !important; }}
      .btn-danger {{ background: #a00; color: #fff; border: none; border-radius: 6px;
                     padding: 8px 16px; font-size: 13px; cursor: pointer; }}
      .btn-danger:hover {{ background: #c00; }}
    </style>
    </head><body>
    <nav><a href="/">← Live Stream</a></nav>
    <h1>Security Dashboard</h1>
    <div class="status">
      <div class="stat">Known people <span>{len(known)}</span></div>
      <div class="stat">Total detections <span>{total}</span></div>
      <div class="stat">Last alert <span>{last_alert}</span></div>
      <div class="stat">Cooldown <span>{COOLDOWN_SECONDS}s</span></div>
      <div class="stat" id="countdown-stat">Cooldown remaining <span id="countdown-val">—</span></div>
    </div>
    <h2>Known People</h2>
    <div class="grid">{known_html}</div>
    <h2>Recent Detections (last 20)</h2>
    <button class="btn-danger" onclick="clearDetections()">Clear All Detections</button>
    <div class="grid" id="det-grid" style="margin-top:12px">{det_html}</div>
    <script>
    function clearDetections() {{
      if (!confirm('Delete all detection photos?')) return;
      fetch('/api/clear_detections', {{method:'POST'}})
        .then(r => r.json())
        .then(d => {{
          document.getElementById('det-grid').innerHTML =
            '<p class="empty">No detections yet.</p>';
        }});
    }}
    (function() {{
      const el = document.getElementById('countdown-val');
      const stat = document.getElementById('countdown-stat');
      function fmt(s) {{
        const m = Math.floor(s / 60), sec = Math.floor(s % 60);
        return m > 0 ? m + 'm ' + String(sec).padStart(2,'0') + 's' : sec + 's';
      }}
      let remaining = 0, lastFetch = 0;
      function tick() {{
        remaining = Math.max(0, remaining - 1);
        if (remaining > 0) {{
          el.textContent = fmt(remaining);
          stat.classList.add('cooldown-active');
        }} else {{
          el.textContent = '—';
          stat.classList.remove('cooldown-active');
        }}
      }}
      function poll() {{
        fetch('/api/status').then(r => r.json()).then(d => {{
          remaining = Math.round(d.remaining);
          tick();
        }});
      }}
      poll();
      setInterval(tick, 1000);
      setInterval(poll, 5000);
    }})();
    </script>
    </body></html>
    """


@app.route("/api/status")
def api_status():
    alert_ts = alerts.last_alert_time()
    remaining = max(0.0, COOLDOWN_SECONDS - (time.time() - alert_ts)) if alert_ts else 0.0
    return jsonify({
        "last_alert_time": alert_ts,
        "cooldown_seconds": COOLDOWN_SECONDS,
        "remaining": remaining,
    })


@app.route("/api/clear_detections", methods=["POST"])
def clear_detections():
    removed = 0
    for f in os.listdir(DETECTIONS_DIR):
        if f.endswith(".jpg"):
            os.remove(os.path.join(DETECTIONS_DIR, f))
            removed += 1
    return jsonify({"removed": removed})


@app.route("/known_faces/<path:filename>")
def serve_known_face(filename):
    return send_from_directory(os.path.abspath(KNOWN_FACES_DIR), filename)


@app.route("/detections/<path:filename>")
def serve_detection(filename):
    return send_from_directory(os.path.abspath(DETECTIONS_DIR), filename)
