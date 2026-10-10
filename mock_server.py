"""Local mock API server for the data regen optimisation exercise.

Serves GET /param1/<id>, /param2/<id>, /param3/<id> as JSON, each with a
small artificial delay to stand in for a slow upstream service. Run this
in its own terminal before running slowdatagen.py.
"""
import json
import random
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HOST = "127.0.0.1"
PORT = 8765
DELAY_SECONDS = 0.05  # simulated per-request latency


class Handler(BaseHTTPRequestHandler):
    def log_message(self, format, *args):
        pass  # keep stdout quiet

    def do_GET(self):
        parts = self.path.strip("/").split("/")
        if len(parts) != 2 or parts[0] not in ("param1", "param2", "param3"):
            self.send_response(404)
            self.end_headers()
            return

        kind, cid = parts
        time.sleep(DELAY_SECONDS)

        # Deterministic per (kind, config_id) so repeated runs are stable.
        random.seed(f"{kind}:{cid}")
        payload = {"config_id": cid, "kind": kind, "value": random.uniform(1, 10)}

        body = json.dumps(payload).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def run(host=HOST, port=PORT):
    server = ThreadingHTTPServer((host, port), Handler)
    print(f"Mock API serving on http://{host}:{port}")
    server.serve_forever()


if __name__ == "__main__":
    run()
