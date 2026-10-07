"""Local bridge: serves the dashboard and relays data from the Python AI pipeline.
Standard library only. Run:  python server.py   ->  http://localhost:8000
Endpoints:
  POST /api/state  JSON {command, detections:[{object,confidence,position,box?}], log_message, demo:false}
  POST /api/frame  raw JPEG bytes (annotated webcam frame from OpenCV)
  GET  /api/state  latest state + age in seconds
  GET  /stream     MJPEG of latest frame
"""
import os, json, time, threading, webbrowser
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler

BASE_DIR = os.path.dirname(os.path.abspath(__file__))

STATE = {"command": None, "detections": [], "log_message": None, "demo": False, "seq": 0}
LAST = {"t": None, "frame": None}


class ReusableThreadingServer(ThreadingHTTPServer):
    allow_reuse_address = True
    daemon_threads = True


class H(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def log_message(self, *a): pass

    def _send(self, code=200, body=b"", ctype="application/json"):
        self.send_response(code)
        self.send_header("Content-Type", ctype)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(204)
        for k, v in (("Access-Control-Allow-Origin", "*"), ("Access-Control-Allow-Headers", "*"),
                     ("Access-Control-Allow-Methods", "GET,POST,OPTIONS")):
            self.send_header(k, v)
        self.end_headers()

    def do_POST(self):
        data = self.rfile.read(int(self.headers.get("Content-Length", 0)))
        if self.path == "/api/state":
            STATE.update(json.loads(data))
            STATE["seq"] = STATE.get("seq", 0) + 1
            LAST["t"] = time.time()
        elif self.path == "/api/frame":
            LAST["frame"] = data
        else:
            return self._send(404)
        self._send(200, b'{"ok":true}')

    def do_GET(self):
        if self.path.startswith("/api/state"):
            age = None if LAST["t"] is None else time.time() - LAST["t"]
            return self._send(200, json.dumps({**STATE, "age": age, "has_frame": LAST["frame"] is not None}).encode())
        if self.path == "/stream":
            self.send_response(200)
            self.send_header("Content-Type", "multipart/x-mixed-replace; boundary=f")
            self.end_headers()
            try:
                while True:
                    if LAST["frame"]:
                        self.wfile.write(b"--f\r\nContent-Type: image/jpeg\r\nContent-Length: %d\r\n\r\n" % len(LAST["frame"]))
                        self.wfile.write(LAST["frame"] + b"\r\n")
                    time.sleep(0.04)
            except Exception:
                return
        return super().do_GET()


def run_server(port=8000, open_browser=True):
    server = ReusableThreadingServer(("0.0.0.0", port), H)
    print(f"[BRIDGE SERVER] Dashboard active at http://localhost:{port}")
    if open_browser:
        threading.Timer(1.0, lambda: webbrowser.open(f"http://localhost:{port}")).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("[BRIDGE SERVER] Shutting down...")
    finally:
        server.server_close()


if __name__ == "__main__":
    run_server(8000, open_browser=True)
