"""Tiny localhost-only HTTP server that backs the settings window."""
import json
import os
import re
import secrets
import subprocess
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import sounddevice as sd

from . import models, netguard, paths


def make_server(ctl):
    token = secrets.token_urlsafe(16)

    class H(BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        # ---- helpers ----
        def _ok_host(self):
            host = self.headers.get("Host", "")
            return host == f"127.0.0.1:{self.server.server_port}"

        def _send(self, code, body, ctype="application/json"):
            if not isinstance(body, (bytes, bytearray)):
                body = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)

        def _authed(self, q):
            return self.headers.get("X-Token") == token or q.get("t", [""])[0] == token

        def _body(self):
            n = int(self.headers.get("Content-Length") or 0)
            return json.loads(self.rfile.read(n) or b"{}") if n else {}

        # ---- routing ----
        def do_GET(self):
            self._route("GET")

        def do_POST(self):
            self._route("POST")

        def _route(self, method):
            if not self._ok_host():
                return self._send(403, {"error": "bad host"})
            u = urlparse(self.path)
            q = parse_qs(u.query)
            p = u.path
            if method == "GET" and p == "/":
                html = open(paths.resource("ui", "index.html"), encoding="utf-8").read()
                return self._send(200, html.replace("__TOKEN__", token).encode(), "text/html; charset=utf-8")
            if not self._authed(q):
                return self._send(403, {"error": "forbidden"})
            try:
                self._api(method, p, q)
            except Exception as e:
                self._send(500, {"error": f"{type(e).__name__}: {e}"})

        def _api(self, method, p, q):
            c = ctl
            if method == "GET" and p == "/api/state":
                return self._send(200, {
                    "state": c.state, "level": round(c.rec.level, 3), "config": c.cfg.snapshot(),
                    "model_ready": models.is_ready(c.cfg["model"]), "download": models.status(),
                    "downloaded": {k: models.is_ready(k) for k in models.MODELS},
                    "attention": c.store.attention_count(), "recovered": c.recovered,
                    "lang": c.lang, "blocked": netguard.blocked, "models_root": models.root(),
                    "models": models.MODELS})
            if method == "GET" and p == "/api/devices":
                devs = [{"id": i, "name": d["name"]} for i, d in enumerate(sd.query_devices())
                        if d["max_input_channels"] > 0 and d["hostapi"] == sd.default.hostapi]
                return self._send(200, devs)
            if method == "POST" and p == "/api/config":
                c.apply_config(self._body())
                return self._send(200, {"ok": True})
            if method == "POST" and p == "/api/hotkey/capture":
                return self._send(200, {"hotkey": c.hotkeys.capture()})
            if method == "POST" and p == "/api/model/download":
                models.download(self._body()["name"])
                return self._send(200, {"ok": True})
            if method == "POST" and p == "/api/model/import":
                b = self._body()
                models.import_model(b.get("path", ""), b.get("name", ""))
                return self._send(200, {"ok": True})
            if method == "POST" and p == "/api/pause":
                c.paused = bool(self._body().get("paused"))
                return self._send(200, {"ok": True})
            if method == "GET" and p == "/api/history":
                rows = c.store.list(q.get("q", [""])[0], trashed=q.get("trash", ["0"])[0] == "1",
                                    attention=q.get("attention", ["0"])[0] == "1")
                for r in rows:
                    r["has_audio"] = bool(r["path"] and os.path.exists(r["path"]))
                return self._send(200, rows)
            m = re.fullmatch(r"/api/history/([\w-]+)/(star|trash|restore|retry)", p)
            if method == "POST" and m:
                rid, act = m.groups()
                if act == "star":
                    row = c.store.get(rid)
                    c.store.update(rid, starred=0 if row["starred"] else 1)
                elif act == "trash":
                    c.trash(rid)
                elif act == "restore":
                    c.restore(rid)
                else:
                    c.retry(rid)
                return self._send(200, {"ok": True})
            m = re.fullmatch(r"/audio/([\w-]+)", p)
            if method == "GET" and m:
                row = c.store.get(m.group(1))
                path = row and (row["path"] or row["trash_path"])
                if not path or not os.path.exists(path):
                    return self._send(404, {"error": "no audio"})
                return self._send(200, open(path, "rb").read(), "audio/wav")
            if method == "POST" and p == "/api/open-folder":
                os.startfile(paths.sub("recordings"))
                return self._send(200, {"ok": True})
            self._send(404, {"error": "not found"})

    srv = ThreadingHTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True, name="http").start()
    return srv, token
