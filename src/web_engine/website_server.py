# ==============================================================================
# OmniHost Pro - Modular Website Engine
# Multi-Site Manager, Drop-in Static/SPA Hosting, Host Header Routing & Telemetry
# ==============================================================================

import os
import sys
import json
import time
import socket
import mimetypes
import threading
from urllib.parse import urlparse, unquote
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Any, Optional

DEFAULT_WEB_PORT = 8090

class WebsiteTelemetry:
    def __init__(self):
        self.lock = threading.Lock()
        self.total_requests = 0
        self.total_bytes = 0
        self.active_connections = 0
        self.visitor_log: List[Dict[str, Any]] = []
        self.status_codes: Dict[int, int] = {}
        self.start_time = time.time()

    def record_request(self, ip: str, method: str, path: str, status: int, size: int):
        with self.lock:
            self.total_requests += 1
            self.total_bytes += size
            self.status_codes[status] = self.status_codes.get(status, 0) + 1
            entry = {
                "timestamp": time.strftime("%H:%M:%S"),
                "ip": ip,
                "method": method,
                "path": path,
                "status": status,
                "size": size
            }
            self.visitor_log.append(entry)
            if len(self.visitor_log) > 200:
                self.visitor_log.pop(0)

    def get_stats(self) -> Dict[str, Any]:
        with self.lock:
            uptime = max(1, int(time.time() - self.start_time))
            qps = round(self.total_requests / uptime, 2)
            return {
                "total_requests": self.total_requests,
                "total_bytes": self.total_bytes,
                "uptime_seconds": uptime,
                "qps": qps,
                "status_codes": dict(self.status_codes),
                "recent_logs": list(self.visitor_log[-20:])
            }

class ModularWebHandler(BaseHTTPRequestHandler):
    server_manager: Any = None

    def log_message(self, format, *args):
        pass # Clean custom telemetry logging

    def _send_json(self, status: int, data: Any):
        body = json.dumps(data).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)
        self.server_manager.telemetry.record_request(
            self.client_address[0], self.command, self.path, status, len(body)
        )

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        # Management API
        if path == "/api/status":
            stats = self.server_manager.telemetry.get_stats()
            stats["active_site"] = self.server_manager.active_site
            stats["available_sites"] = self.server_manager.list_available_sites()
            stats["active_port"] = self.server_manager.port
            self._send_json(200, stats)
            return

        elif path == "/api/sites":
            self._send_json(200, {
                "active_site": self.server_manager.active_site,
                "sites": self.server_manager.list_available_sites()
            })
            return

        # Serve static site file
        self._serve_site_file(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)

        if path == "/api/switch-site":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                target_site = body.get("site_name")
                if self.server_manager.set_active_site(target_site):
                    self._send_json(200, {"status": "ok", "active_site": target_site})
                else:
                    self._send_json(400, {"error": f"Site '{target_site}' does not exist"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        self._send_json(404, {"error": "Endpoint not found"})

    def _serve_site_file(self, req_path: str):
        # Resolve target site based on Host header or active site
        host_hdr = self.headers.get("Host", "").split(":")[0].strip().lower()
        site_root = self.server_manager.resolve_site_root(host_hdr)

        clean_path = req_path.lstrip("/")
        if not clean_path:
            clean_path = "index.html"

        file_path = os.path.normpath(os.path.join(site_root, clean_path))
        # Directory traversal guard
        if not file_path.startswith(site_root):
            self.send_error(403, "Access Forbidden")
            return

        # If directory, look for index.html inside
        if os.path.isdir(file_path):
            idx = os.path.join(file_path, "index.html")
            if os.path.isfile(idx):
                file_path = idx

        # SPA router fallback: if file does not exist and has no dot extension, fall back to index.html
        if not os.path.isfile(file_path):
            _, ext = os.path.splitext(clean_path)
            if not ext:
                spa_idx = os.path.join(site_root, "index.html")
                if os.path.isfile(spa_idx):
                    file_path = spa_idx

        if not os.path.isfile(file_path):
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            body = (
                "<!DOCTYPE html><html><head><title>404 Not Found</title>"
                "<style>body{font-family:sans-serif;background:#0F172A;color:#F8FAFC;display:flex;align-items:center;justify-content:center;height:100vh;margin:0;}"
                ".c{text-align:center;padding:40px;background:#1E293B;border-radius:12px;box-shadow:0 10px 25px rgba(0,0,0,0.5);}"
                "h1{color:#EF4444;margin:0 0 10px 0;}p{color:#94A3B8;}</style></head>"
                f"<body><div class='c'><h1>404 Not Found</h1><p>The requested path <code>{req_path}</code> was not found on OmniHost Pro.</p></div></body></html>"
            ).encode("utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            self.server_manager.telemetry.record_request(self.client_address[0], self.command, req_path, 404, len(body))
            return

        # File exists: determine MIME type and stream
        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            if file_path.endswith(".wasm"): mime_type = "application/wasm"
            elif file_path.endswith(".webp"): mime_type = "image/webp"
            elif file_path.endswith(".svg"): mime_type = "image/svg+xml"
            elif file_path.endswith(".woff2"): mime_type = "font/woff2"
            else: mime_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "public, max-age=3600")
            self.end_headers()
            self.wfile.write(content)
            self.server_manager.telemetry.record_request(
                self.client_address[0], self.command, req_path, 200, len(content)
            )
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

class ModularWebsiteServer:
    def __init__(self, sites_dir: Optional[str] = None, default_site: str = "default", port: int = DEFAULT_WEB_PORT):
        if sites_dir is None:
            self.sites_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sites")
        else:
            self.sites_dir = os.path.abspath(sites_dir)

        os.makedirs(self.sites_dir, exist_ok=True)
        self.active_site = default_site
        self.port = port
        self.telemetry = WebsiteTelemetry()
        self.http_server = None
        self.server_thread = None
        self.is_running = False

        self._ensure_site_exists(self.active_site)

    def _ensure_site_exists(self, site_name: str):
        path = os.path.join(self.sites_dir, site_name)
        os.makedirs(path, exist_ok=True)
        idx = os.path.join(path, "index.html")
        if not os.path.exists(idx):
                with open(idx, "w", encoding="utf-8") as f:
                    f.write(
                        "<!DOCTYPE html><html><head><meta charset='utf-8'><title>Welcome to OmniHost Pro</title>"
                        "<style>body{background:#090B10;color:#F8FAFC;font-family:-apple-system,BlinkMacSystemFont,Segoe UI,Roboto,sans-serif;margin:0;display:flex;align-items:center;justify-content:center;height:100vh;text-align:center;}"
                        ".card{background:#131722;padding:48px 64px;border-radius:16px;border:1px solid #242C40;box-shadow:0 20px 40px rgba(0,0,0,0.6);max-width:540px;}"
                        "h1{color:#10B981;font-size:2.2rem;margin:0 0 12px 0;letter-spacing:-0.5px;}p{color:#94A3B8;line-height:1.6;font-size:1.05rem;}"
                        ".badge{display:inline-block;padding:6px 14px;background:#1B2030;border:1px solid #10B981;color:#10B981;border-radius:20px;font-size:0.85rem;font-weight:600;margin-bottom:16px;}"
                        ".btn{display:inline-block;margin-top:20px;padding:12px 28px;background:#10B981;color:#000;text-decoration:none;font-weight:bold;border-radius:8px;}</style></head>"
                        f"<body><div class='card'><div class='badge'>OmniHost Pro Cloud Server</div><h1>Your Site is Live!</h1>"
                        f"<p>Hosted cleanly on <strong>{site_name}</strong>. Drop your HTML, CSS, React build, or Hugo/Vite export directly into <code>sites/{site_name}/</code> to update live.</p>"
                        "</div></body></html>"
                    )

    def list_available_sites(self) -> List[str]:
        if not os.path.exists(self.sites_dir):
            return []
        sites = [d for d in os.listdir(self.sites_dir) if os.path.isdir(os.path.join(self.sites_dir, d))]
        return sorted(sites)

    def set_active_site(self, site_name: str) -> bool:
        path = os.path.join(self.sites_dir, site_name)
        if os.path.isdir(path):
            self.active_site = site_name
            return True
        return False

    def resolve_site_root(self, host: str) -> str:
        # Check if domain-specific folder exists (e.g. sites/mysite.com)
        if host:
            host_path = os.path.join(self.sites_dir, host)
            if os.path.isdir(host_path):
                return host_path
        # Fallback to active site
        active_path = os.path.join(self.sites_dir, self.active_site)
        if os.path.isdir(active_path):
            return active_path
        return self.sites_dir

    def start(self):
        if self.is_running:
            return
        ModularWebHandler.server_manager = self
        self.http_server = ThreadingHTTPServer(("0.0.0.0", self.port), ModularWebHandler)
        self.server_thread = threading.Thread(target=self.http_server.serve_forever, daemon=True, name="OmniHostWebThread")
        self.server_thread.start()
        self.is_running = True

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        if self.http_server:
            self.http_server.shutdown()
            self.http_server.server_close()

if __name__ == "__main__":
    server = ModularWebsiteServer(port=DEFAULT_WEB_PORT)
    server.start()
    print(f"OmniHost Pro Website Server running on http://127.0.0.1:{DEFAULT_WEB_PORT}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        server.stop()
        print("Stopped website server.")
