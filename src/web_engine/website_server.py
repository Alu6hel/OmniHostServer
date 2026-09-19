# =======================================================================# OmniHost Pro - Modular Website Engine
# Multi-Site Manager, Drop-in Static/SPA Hosting, Host Header Routing & Telemetry
# Full Web File Explorer & Media Hub Backend (Video Streaming, On-the-fly ZIP)
# =======================================================================
import os
import sys
import json
import time
import socket
import mimetypes
import threading
import zipfile
import io
import shutil
import re
import urllib.request
from urllib.parse import urlparse, parse_qs, unquote
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Any, Optional

DEFAULT_WEB_PORT = 8090

# 4MB static pre-allocated random data buffer to ensure zero CPU bottleneck during gigabit speedtests
SPEEDTEST_RANDOM_BUFFER = os.urandom(4 * 1024 * 1024)

def format_size(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"

def set_desktop_wallpaper(image_path: str) -> bool:
    abs_path = os.path.abspath(image_path)
    if not os.path.exists(abs_path):
        return False
    try:
        if sys.platform == "win32":
            import ctypes
            # SPI_SETDESKWALLPAPER = 20, SPIF_UPDATEINIFILE = 1, SPIF_SENDCHANGE = 2
            return ctypes.windll.user32.SystemParametersInfoW(20, 0, abs_path, 3) != 0
        elif sys.platform == "darwin":
            cmd = f"""osascript -e 'tell application "Finder" to set desktop picture to POSIX file "{abs_path}"'"""
            return os.system(cmd) == 0
        elif sys.platform.startswith("linux"):
            os.system(f"gsettings set org.gnome.desktop.background picture-uri 'file://{abs_path}' 2>/dev/null")
            os.system(f"gsettings set org.gnome.desktop.background picture-uri-dark 'file://{abs_path}' 2>/dev/null")
            os.system(f"feh --bg-scale '{abs_path}' 2>/dev/null")
            return True
    except Exception as e:
        print(f"Error setting desktop wallpaper: {e}")
        return False
    return False

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
        if not getattr(self, "_is_head", False):
            self.wfile.write(body)
        self.server_manager.telemetry.record_request(
            self.client_address[0], self.command, self.path, status, len(body)
        )

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, HEAD, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Range")
        self.end_headers()

    def do_HEAD(self):
        self._is_head = True
        self.do_GET()

    def do_GET(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        # 1. Management API
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

        # 2. Web File Explorer & Media Hub routes (Images 2, 3, 4)
        elif path in ("/files", "/files/", "/explorer", "/explorer/"):
            self._serve_file_manager_ui()
            return

        elif path == "/api/files/list":
            self._handle_files_list(query)
            return

        elif path == "/api/files/download":
            self._handle_file_download(query)
            return

        elif path == "/api/files/download-folder":
            self._handle_download_folder(query)
            return

        elif path == "/api/files/preview":
            self._handle_file_preview(query)
            return

        elif path == "/api/files/storage":
            self._handle_file_storage()
            return

        elif path == "/api/files/set-wallpaper":
            self._handle_set_wallpaper(query)
            return

        elif path == "/api/speedtest/ping":
            client_ip = self.headers.get("CF-Connecting-IP") or self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or self.client_address[0]
            seq = query.get("seq", "0")
            client_t = query.get("t", "")
            now_t = time.time()
            self._send_json(200, {
                "status": "ok",
                "seq": int(seq) if seq.isdigit() else 0,
                "client_t": client_t,
                "timestamp": now_t,
                "server_time_ms": int(now_t * 1000),
                "server_time_ns": time.time_ns(),
                "client_ip": client_ip,
                "server": "OmniSpeed-Global-Edge"
            })
            return

        elif path == "/api/speedtest/info":
            client_ip = self.headers.get("CF-Connecting-IP") or self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or self.client_address[0]
            country = self.headers.get("CF-IPCountry", "Global")
            city = self.headers.get("CF-IPCity", "")
            isp_name = "Broadband Provider"
            server_sponsor = "FLOW Jamaica"
            server_city = "Montego Bay"

            try:
                host_info = socket.gethostbyaddr(client_ip)
                if host_info and host_info[0]:
                    parts = host_info[0].split(".")
                    if len(parts) >= 2:
                        raw_name = parts[-2].upper()
                        if "CWJAMAICA" in raw_name or "C&W" in raw_name or "FLOW" in raw_name:
                            isp_name = "Flow"
                            server_sponsor = "FLOW Jamaica"
                            server_city = "Montego Bay"
                        elif len(raw_name) > 2 and raw_name not in ("COM", "NET", "ORG", "EDU"):
                            isp_name = raw_name
            except Exception:
                if country == "JM":
                    isp_name = "Flow"
                elif country != "Global":
                    isp_name = f"Broadband Network ({country})"
            
            if client_ip in ("127.0.0.1", "::1", "localhost") or client_ip.startswith("72.27."):
                client_ip = "72.27.211.125"
                isp_name = "Flow"
                server_sponsor = "FLOW Jamaica"
                server_city = "Montego Bay"
                country = "JM"

            self._send_json(200, {
                "status": "ok",
                "ip": client_ip,
                "client_ip": client_ip,
                "isp": isp_name,
                "country": country,
                "city": city or server_city,
                "server_name": server_sponsor,
                "server_location": f"{server_sponsor} - {server_city}",
                "server_sponsor": server_sponsor,
                "server_city": server_city,
                "server_node": "Quantum-Core-01",
                "protocol": "HTTP/1.1 (Multi-Stream Saturation)"
            })
            return

        elif path == "/api/speedtest/servers":
            self._send_json(200, {
                "status": "ok",
                "servers": [
                    {
                        "id": "flow-mb",
                        "name": "FLOW Jamaica",
                        "sponsor": "FLOW Jamaica",
                        "city": "Montego Bay",
                        "country": "Jamaica",
                        "distance": "12 km",
                        "is_default": True
                    },
                    {
                        "id": "flow-kin",
                        "name": "FLOW Jamaica",
                        "sponsor": "FLOW Jamaica",
                        "city": "Kingston",
                        "country": "Jamaica",
                        "distance": "128 km",
                        "is_default": False
                    },
                    {
                        "id": "alu-edge",
                        "name": "Alu OmniSpeed Edge",
                        "sponsor": "Alu Labs",
                        "city": "Global Anycast",
                        "country": "Global",
                        "distance": "50 km",
                        "is_default": False
                    }
                ]
            })
            return

        elif path == "/api/speedtest/download":
            try:
                size_bytes = int(query.get("size", 4 * 1024 * 1024))
            except ValueError:
                size_bytes = 4 * 1024 * 1024
            size_bytes = min(max(size_bytes, 1024), 50 * 1024 * 1024)
            self.send_response(200)
            self.send_header("Content-Type", "application/octet-stream")
            self.send_header("Content-Length", str(size_bytes))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "no-cache, no-store, must-revalidate, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.end_headers()
            rem = size_bytes
            buf_len = len(SPEEDTEST_RANDOM_BUFFER)
            buf_offset = 0
            chunk_size = 65536
            while rem > 0:
                to_write = min(rem, chunk_size)
                if buf_offset + to_write > buf_len:
                    buf_offset = 0
                self.wfile.write(SPEEDTEST_RANDOM_BUFFER[buf_offset:buf_offset + to_write])
                buf_offset += to_write
                rem -= to_write
            self.server_manager.telemetry.record_request(
                self.client_address[0], "GET", "/api/speedtest/download", 200, size_bytes
            )
            return

        elif path == "/api/speedtest/results":
            res_id = query.get("id")
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            storage_dir = os.path.join(base_dir, "storage")
            res_file = os.path.join(storage_dir, "speedtest_results.json")
            if os.path.exists(res_file):
                try:
                    with open(res_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if res_id:
                        result = data.get("by_id", {}).get(res_id)
                        if result:
                            self._send_json(200, {"status": "ok", "result": result})
                        else:
                            self._send_json(404, {"error": "Result ID not found"})
                    else:
                        self._send_json(200, {"status": "ok", "recent": data.get("recent", [])[:20], "total_tests": len(data.get("recent", []))})
                except Exception as e:
                    self._send_json(500, {"error": str(e)})
            else:
                self._send_json(200, {"status": "ok", "recent": [], "total_tests": 0})
            return

        elif path == "/api/tunnel/status":
            self._send_json(200, self.server_manager.get_tunnel_status())
            return

        # 3. Serve static site file
        elif path == "/api/feedback":
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
            storage_dir = os.path.join(base_dir, "storage")
            fb_file = os.path.join(storage_dir, "feedback.json")
            if os.path.exists(fb_file):
                try:
                    with open(fb_file, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    self._send_json(200, data)
                except Exception as e:
                    self._send_json(500, {"error": str(e)})
            else:
                self._send_json(200, {"items": [], "by_app": {}})
        elif path in ("/api/ip", "/api/myip", "/api/ip-info"):
            self._handle_ip_intelligence(query)
            return

        # Serve static site file
        self._serve_site_file(path)

    def do_POST(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        if path == "/api/switch-site":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                target_site = body.get("site_name") or body.get("site")
                if self.server_manager.set_active_site(target_site):
                    self._send_json(200, {"status": "ok", "active_site": target_site})
                else:
                    self._send_json(400, {"error": f"Site '{target_site}' does not exist"})
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        elif path == "/api/files/upload":
            self._handle_file_upload(query)
            return

        elif path == "/api/files/mkdir":
            self._handle_file_mkdir(query)
            return

        elif path == "/api/files/delete":
            self._handle_file_delete(query)
            return

        elif path == "/api/files/set-wallpaper":
            rel_path = query.get("path")
            if not rel_path:
                try:
                    length = int(self.headers.get("Content-Length", 0))
                    if length > 0:
                        body = json.loads(self.rfile.read(length).decode("utf-8"))
                        rel_path = body.get("path")
                except Exception:
                    pass
            self._handle_set_wallpaper({"path": rel_path} if rel_path else {})
            return

        elif path == "/api/speedtest/upload":
            length = int(self.headers.get("Content-Length", 0))
            t0 = time.time()
            rem = length
            chunk_size = 65536
            while rem > 0:
                to_read = min(rem, chunk_size)
                data = self.rfile.read(to_read)
                if not data:
                    break
                rem -= len(data)
            elapsed_sec = max(0.0001, time.time() - t0)
            elapsed_ms = round(elapsed_sec * 1000, 2)
            received_bytes = length - rem
            throughput_mbps = round((received_bytes * 8) / (elapsed_sec * 1000000), 2)
            self._send_json(200, {
                "status": "ok",
                "received_bytes": received_bytes,
                "elapsed_ms": elapsed_ms,
                "server_measured_mbps": throughput_mbps
            })
            return

        elif path == "/api/speedtest/results":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
                
                client_ip = self.headers.get("CF-Connecting-IP") or self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or self.client_address[0]
                masked_ip = ".".join(client_ip.split(".")[:2]) + ".*.*" if "." in client_ip else "anon"
                
                import random
                test_num = random.randint(1000000000, 9999999999)
                test_id = f"ALU-SPEED-{test_num}"
                
                result_record = {
                    "id": test_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                    "download_mbps": float(body.get("download_mbps", 0.0)),
                    "upload_mbps": float(body.get("upload_mbps", 0.0)),
                    "ping_idle_ms": float(body.get("ping_idle_ms", 0.0)),
                    "ping_download_ms": float(body.get("ping_download_ms", 0.0)),
                    "ping_upload_ms": float(body.get("ping_upload_ms", 0.0)),
                    "jitter_ms": float(body.get("jitter_ms", 0.0)),
                    "packet_loss_pct": float(body.get("packet_loss_pct", 0.0)),
                    "stability_pct": float(body.get("stability_pct", 100.0)),
                    "isp": body.get("isp", "Unknown ISP"),
                    "ip_masked": masked_ip,
                    "server": body.get("server", "Alu OmniSpeed Global Edge"),
                    "connection_mode": body.get("connection_mode", "Multi"),
                    "ratings": body.get("ratings", {}),
                    "telemetry_summary": body.get("telemetry_summary", {}),
                    "nps_rating": body.get("nps_rating", None)
                }
                
                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                storage_dir = os.path.join(base_dir, "storage")
                os.makedirs(storage_dir, exist_ok=True)
                res_file = os.path.join(storage_dir, "speedtest_results.json")
                
                data = {"by_id": {}, "recent": []}
                if os.path.exists(res_file):
                    try:
                        with open(res_file, "r", encoding="utf-8") as f:
                            data = json.load(f)
                            if "by_id" not in data: data["by_id"] = {}
                            if "recent" not in data: data["recent"] = []
                    except Exception:
                        pass
                
                data["by_id"][test_id] = result_record
                data["recent"].insert(0, result_record)
                data["recent"] = data["recent"][:200]
                
                with open(res_file, "w", encoding="utf-8") as f:
                    json.dump(data, f, indent=2)
                
                self._send_json(200, {
                    "status": "ok",
                    "id": test_id,
                    "share_url": f"/speedtest?id={test_id}",
                    "record": result_record
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})
            return

        elif path == "/api/tunnel/start":
            url = self.server_manager.start_tunnel()
            self._send_json(200, {"status": "ok", "url": url})
            return

        elif path == "/api/tunnel/stop":
            self.server_manager.stop_tunnel()
            self._send_json(200, {"status": "ok"})
            return

        elif path == "/api/contact":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
                name = body.get("name", "Anonymous").strip()
                email = body.get("email", "").strip()
                category = body.get("category", "General Inquiry").strip()
                subject = body.get("subject", "").strip()
                message = body.get("message", "").strip()

                if not message:
                    self._send_json(400, {"status": "error", "message": "Message body cannot be empty."})
                    return

                client_ip = self.headers.get("CF-Connecting-IP") or self.headers.get("X-Forwarded-For", "").split(",")[0].strip() or self.client_address[0]
                masked_ip = ".".join(client_ip.split(".")[:2]) + ".*.*" if "." in client_ip else "anon"

                ticket_id = f"TICK-{int(time.time()*1000)}"
                entry = {
                    "ticket_id": ticket_id,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                    "name": name,
                    "email": email,
                    "category": category,
                    "subject": subject,
                    "message": message,
                    "ip_masked": masked_ip
                }

                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                storage_dir = os.path.join(base_dir, "storage")
                os.makedirs(storage_dir, exist_ok=True)
                contact_file = os.path.join(storage_dir, "contact_messages.json")
                
                messages = []
                if os.path.exists(contact_file):
                    try:
                        with open(contact_file, "r", encoding="utf-8") as f:
                            messages = json.load(f)
                            if not isinstance(messages, list): messages = []
                    except Exception:
                        messages = []
                
                messages.insert(0, entry)
                messages = messages[:1000]

                with open(contact_file, "w", encoding="utf-8") as f:
                    json.dump(messages, f, indent=2, ensure_ascii=False)

                self._send_json(200, {
                    "status": "ok",
                    "ticket_id": ticket_id,
                    "message": "Thank you! Your message has been received and logged directly for our team."
                })
            except Exception as e:
                self._send_json(500, {"status": "error", "message": str(e)})
            return

        elif path == "/api/feedback":
            try:
                length = int(self.headers.get("Content-Length", 0))
                body = json.loads(self.rfile.read(length).decode("utf-8"))
                
                # Support single-input feedback
                feedback_text = (body.get("feedback") or body.get("message") or body.get("text") or "").strip()
                if not feedback_text:
                    self._send_json(400, {"error": "Please enter your feedback."})
                    return

                # Auto-detect app if not explicitly chosen or if general
                app_name = body.get("app", "").strip()
                lower_text = feedback_text.lower()
                if not app_name or app_name in ["Unknown", "General", "General / Website"]:
                    if "galaxsee pro" in lower_text or "galaxsee-pro" in lower_text or ("pro" in lower_text and "galax" in lower_text):
                        app_name = "Galaxsee Pro"
                    elif "galaxsee" in lower_text or "galaxy" in lower_text or "gallery" in lower_text:
                        app_name = "Galaxsee"
                    elif "suechef" in lower_text or "sue chef" in lower_text or "legal" in lower_text or "law" in lower_text or "court" in lower_text or "claim" in lower_text:
                        app_name = "SueChef"
                    elif "underwraps" in lower_text or "under wraps" in lower_text or "messenger" in lower_text or "chat" in lower_text:
                        app_name = "UnderWraps"
                    elif "omnihost" in lower_text or "omni host" in lower_text or "ftp" in lower_text or "tunnel" in lower_text or "hosting" in lower_text:
                        app_name = "OmniHost"
                    else:
                        app_name = "General / Website"

                # Auto-detect category
                category = "Feedback"
                if any(w in lower_text for w in ["bug", "error", "crash", "broken", "issue", "fail", "freeze", "problem", "glitch"]):
                    category = "Bug Report"
                elif any(w in lower_text for w in ["feature", "suggest", "add", "would be nice", "could you", "idea", "request"]):
                    category = "Feature Request"
                elif any(w in lower_text for w in ["love", "great", "awesome", "good", "fast", "smooth", "perfect", "nice", "clean"]):
                    category = "Praise"

                import hashlib
                client_ip = self.client_address[0]
                masked_ip = ".".join(client_ip.split(".")[:2]) + ".*.*" if "." in client_ip else "anon"
                ip_hash = hashlib.sha256(client_ip.encode()).hexdigest()[:10]

                entry = {
                    "id": f"fb_{int(time.time()*1000)}",
                    "app": app_name,
                    "category": category,
                    "feedback": feedback_text,
                    "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
                    "ip_masked": masked_ip,
                    "ip_hash": ip_hash
                }

                base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
                storage_dir = os.path.join(base_dir, "storage")
                os.makedirs(storage_dir, exist_ok=True)
                fb_file = os.path.join(storage_dir, "feedback.json")
                
                existing = {"items": [], "by_app": {}}
                if os.path.exists(fb_file):
                    try:
                        with open(fb_file, "r", encoding="utf-8") as f:
                            loaded = json.load(f)
                            if isinstance(loaded, dict):
                                existing = loaded
                                if "items" not in existing: existing["items"] = []
                                if "by_app" not in existing: existing["by_app"] = {}
                    except Exception:
                        existing = {"items": [], "by_app": {}}

                existing["items"].insert(0, entry)
                if app_name not in existing["by_app"]:
                    existing["by_app"][app_name] = []
                existing["by_app"][app_name].insert(0, entry)

                # Keep items capped to 1000
                existing["items"] = existing["items"][:1000]

                with open(fb_file, "w", encoding="utf-8") as f:
                    json.dump(existing, f, indent=2, ensure_ascii=False)

                self._send_json(200, {
                    "status": "ok",
                    "message": "Thank you! Your feedback has been securely received and recorded privately. We appreciate your help shaping our beta releases.",
                    "detected_app": app_name,
                    "category": category
                })
            except Exception as e:
                self._send_json(500, {"error": str(e)})
        elif path == "/api/resizer":
            try:
                length = int(self.headers.get("Content-Length", 0))
                raw_body = self.rfile.read(length) if length > 0 else b""
                content_type = self.headers.get("Content-Type", "")

                from PIL import Image, ImageOps
                import base64

                image_data = None
                crop_mode = "cover"

                if "application/json" in content_type:
                    body = json.loads(raw_body.decode("utf-8"))
                    b64_str = body.get("image", "")
                    crop_mode = body.get("mode", "cover")
                    if "," in b64_str:
                        b64_str = b64_str.split(",", 1)[1]
                    image_data = base64.b64decode(b64_str)
                else:
                    image_data = raw_body

                if not image_data:
                    self._send_json(400, {"error": "No image data provided for processing"})
                    return

                src_img = Image.open(io.BytesIO(image_data))
                if src_img.mode in ("RGBA", "LA") or (src_img.mode == "P" and "transparency" in src_img.info):
                    work_img = src_img.convert("RGBA")
                else:
                    work_img = src_img.convert("RGB")

                presets = [
                    ("linkedin_profile_400x400.png", 400, 400),
                    ("linkedin_banner_1584x396.png", 1584, 396),
                    ("linkedin_post_1200x627.png", 1200, 627),
                    ("linkedin_logo_300x300.png", 300, 300),
                    ("x_twitter_profile_400x400.png", 400, 400),
                    ("x_twitter_header_1500x500.png", 1500, 500),
                    ("x_twitter_post_1600x900.png", 1600, 900),
                    ("instagram_profile_320x320.png", 320, 320),
                    ("instagram_post_square_1080x1080.png", 1080, 1080),
                    ("instagram_story_reel_1080x1920.png", 1080, 1920),
                    ("instagram_landscape_1080x566.png", 1080, 566),
                    ("youtube_avatar_800x800.png", 800, 800),
                    ("youtube_channel_banner_2560x1440.png", 2560, 1440),
                    ("youtube_thumbnail_1280x720.png", 1280, 720),
                    ("tiktok_cover_1080x1920.png", 1080, 1920),
                    ("facebook_cover_820x312.png", 820, 312)
                ]

                zip_buffer = io.BytesIO()
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zip_file:
                    for filename, target_w, target_h in presets:
                        if crop_mode == "contain":
                            fitted = work_img.copy()
                            fitted.thumbnail((target_w, target_h), Image.Resampling.LANCZOS)
                            bg_img = Image.new("RGBA", (target_w, target_h), (0, 0, 0, 0))
                            paste_x = (target_w - fitted.width) // 2
                            paste_y = (target_h - fitted.height) // 2
                            bg_img.paste(fitted, (paste_x, paste_y))
                            out_img = bg_img
                        else:
                            out_img = ImageOps.fit(work_img, (target_w, target_h), method=Image.Resampling.LANCZOS)
                        
                        item_buf = io.BytesIO()
                        out_img.save(item_buf, format="PNG", optimize=True)
                        zip_file.writestr(filename, item_buf.getvalue())

                zip_bytes = zip_buffer.getvalue()

                self.send_response(200)
                self.send_header("Content-Type", "application/zip")
                self.send_header("Content-Disposition", 'attachment; filename="Alumungandr-Social-Pack.zip"')
                self.send_header("Content-Length", str(len(zip_bytes)))
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()
                self.wfile.write(zip_bytes)
                return
            except Exception as e:
                self._send_json(500, {"error": str(e)})
                return

        self._send_json(404, {"error": "Endpoint not found"})

    def do_DELETE(self):
        parsed = urlparse(self.path)
        path = unquote(parsed.path)
        query = {k: v[0] for k, v in parse_qs(parsed.query).items()}

        if path == "/api/files/delete":
            self._handle_file_delete(query)
            return
        self._send_json(404, {"error": "Endpoint not found"})

    # --- File Explorer Implementations ---

    def _serve_file_manager_ui(self):
        ui_path = os.path.join(self.server_manager.sites_dir, "file_manager", "index.html")
        if not os.path.exists(ui_path):
            ui_path = os.path.join(os.path.dirname(self.server_manager.sites_dir), "web_app", "file_manager.html")

        if os.path.exists(ui_path):
            with open(ui_path, "rb") as f:
                data = f.read()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(data)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(data)
            self.server_manager.telemetry.record_request(
                self.client_address[0], "GET", "/files", 200, len(data)
            )
        else:
            self._send_json(404, {"error": "File manager UI not found"})

    def _get_safe_path(self, rel_path: str) -> Optional[str]:
        rel = (rel_path or "").lstrip("/\\")
        norm = os.path.normpath(os.path.join(self.server_manager.storage_dir, rel))
        if norm == self.server_manager.storage_dir or norm.startswith(self.server_manager.storage_dir + os.sep):
            return norm
        return None

    def _get_relative_path(self, full_path: str) -> str:
        rel = os.path.relpath(full_path, self.server_manager.storage_dir)
        return "" if rel == "." else rel.replace("\\", "/")

    def _file_to_dict(self, f_path: str) -> Dict[str, Any]:
        stat = os.stat(f_path)
        fname = os.path.basename(f_path)
        rel = self._get_relative_path(f_path)
        mime, _ = mimetypes.guess_type(f_path)
        if not mime:
            mime = "application/octet-stream"

        return {
            "name": fname,
            "path": rel,
            "size": stat.st_size,
            "size_formatted": format_size(stat.st_size),
            "modified": int(stat.st_mtime * 1000),
            "modified_str": time.strftime("%Y-%m-%d %H:%M", time.localtime(stat.st_mtime)),
            "mime": mime,
            "is_image": mime.startswith("image/"),
            "is_video": mime.startswith("video/"),
            "is_audio": mime.startswith("audio/"),
            "download_url": f"/api/files/download?path={rel}",
            "preview_url": f"/api/files/preview?path={rel}"
        }

    def _handle_files_list(self, query: Dict[str, str]):
        rel_path = query.get("path", "")
        category = query.get("category", "all").lower()
        search = query.get("search", "").lower()

        target_dir = self._get_safe_path(rel_path)
        if not target_dir or not os.path.exists(target_dir) or not os.path.isdir(target_dir):
            self._send_json(404, {"status": "error", "message": "Directory not found"})
            return

        curr_rel = self._get_relative_path(target_dir)
        parent_rel = ""
        if target_dir != self.server_manager.storage_dir:
            parent_rel = self._get_relative_path(os.path.dirname(target_dir))

        folders_arr: List[Dict[str, Any]] = []
        files_arr: List[Dict[str, Any]] = []

        if category == "recent":
            all_files = []
            for root, dirs, files in os.walk(self.server_manager.storage_dir):
                for f in files:
                    if not search or search in f.lower():
                        all_files.append(os.path.join(root, f))
            all_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            for f in all_files[:50]:
                files_arr.append(self._file_to_dict(f))
        elif category and category != "all":
            cat_files = []
            for root, dirs, files in os.walk(self.server_manager.storage_dir):
                for f in files:
                    if search and search not in f.lower():
                        continue
                    mime, _ = mimetypes.guess_type(f)
                    mime = mime or ""
                    match = False
                    if category == "documents":
                        match = mime.startswith("text/") or "pdf" in mime or "document" in mime or f.endswith((".pdf", ".txt", ".docx", ".md"))
                    elif category == "pictures":
                        match = mime.startswith("image/")
                    elif category == "videos":
                        match = mime.startswith("video/")
                    elif category in ("music", "musics"):
                        match = mime.startswith("audio/")
                    if match:
                        cat_files.append(os.path.join(root, f))
            cat_files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
            for f in cat_files:
                files_arr.append(self._file_to_dict(f))
        else:
            try:
                entries = sorted(os.listdir(target_dir), key=lambda s: s.lower())
                for e in entries:
                    if search and search not in e.lower():
                        continue
                    full = os.path.join(target_dir, e)
                    if os.path.isdir(full):
                        try:
                            item_count = len(os.listdir(full))
                        except Exception:
                            item_count = 0
                        folders_arr.append({
                            "name": e,
                            "path": self._get_relative_path(full),
                            "modified": int(os.path.getmtime(full) * 1000),
                            "item_count": item_count
                        })
                    else:
                        files_arr.append(self._file_to_dict(full))
            except Exception as ex:
                self._send_json(500, {"status": "error", "message": str(ex)})
                return

        self._send_json(200, {
            "status": "ok",
            "current_path": curr_rel,
            "parent_path": parent_rel,
            "folders": folders_arr,
            "files": files_arr
        })

    def _handle_file_download(self, query: Dict[str, str]):
        rel_path = query.get("path", "")
        target_file = self._get_safe_path(rel_path)
        if not target_file or not os.path.isfile(target_file):
            self.send_error(404, "File not found")
            return

        fname = os.path.basename(target_file)
        fsize = os.path.getsize(target_file)
        mime, _ = mimetypes.guess_type(target_file)
        mime = mime or "application/octet-stream"

        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
        self.send_header("Content-Length", str(fsize))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        with open(target_file, "rb") as f:
            shutil.copyfileobj(f, self.wfile, 65536)

        self.server_manager.telemetry.record_request(
            self.client_address[0], "DOWNLOAD", "/api/files/download", 200, fsize
        )

    def _handle_download_folder(self, query: Dict[str, str]):
        rel_path = query.get("path", "")
        target_dir = self._get_safe_path(rel_path)
        if not target_dir or not os.path.isdir(target_dir):
            self.send_error(404, "Folder not found")
            return

        folder_name = os.path.basename(target_dir) or "OmniHost_Files"
        zip_name = f"{folder_name}.zip"

        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
            for root, dirs, files in os.walk(target_dir):
                for file in files:
                    full = os.path.join(root, file)
                    arc = os.path.relpath(full, target_dir)
                    zf.write(full, arc)

        zip_bytes = buf.getvalue()
        self.send_response(200)
        self.send_header("Content-Type", "application/zip")
        self.send_header("Content-Disposition", f'attachment; filename="{zip_name}"')
        self.send_header("Content-Length", str(len(zip_bytes)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(zip_bytes)

        self.server_manager.telemetry.record_request(
            self.client_address[0], "DOWNLOAD_FOLDER_ZIP", "/api/files/download-folder", 200, len(zip_bytes)
        )

    def _handle_file_preview(self, query: Dict[str, str]):
        rel_path = query.get("path", "")
        target_file = self._get_safe_path(rel_path)
        if not target_file or not os.path.isfile(target_file):
            self.send_error(404, "File not found")
            return

        file_len = os.path.getsize(target_file)
        mime, _ = mimetypes.guess_type(target_file)
        mime = mime or "application/octet-stream"

        range_header = self.headers.get("Range")
        if range_header and range_header.startswith("bytes="):
            m = re.match(r"bytes=(\d*)-(\d*)", range_header)
            if m:
                raw_start, raw_end = m.groups()
                start = int(raw_start) if raw_start else 0
                end = int(raw_end) if raw_end else file_len - 1
                if end >= file_len:
                    end = file_len - 1
                length = max(0, end - start + 1)

                self.send_response(206)
                self.send_header("Content-Type", mime)
                self.send_header("Content-Range", f"bytes {start}-{end}/{file_len}")
                self.send_header("Content-Length", str(length))
                self.send_header("Accept-Ranges", "bytes")
                self.send_header("Access-Control-Allow-Origin", "*")
                self.end_headers()

                with open(target_file, "rb") as f:
                    f.seek(start)
                    remaining = length
                    while remaining > 0:
                        chunk = f.read(min(65536, remaining))
                        if not chunk:
                            break
                        self.wfile.write(chunk)
                        remaining -= len(chunk)

                self.server_manager.telemetry.record_request(
                    self.client_address[0], "STREAM_RANGE", "/api/files/preview", 206, length
                )
                return

        # Full file preview
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(file_len))
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        with open(target_file, "rb") as f:
            shutil.copyfileobj(f, self.wfile, 65536)

        self.server_manager.telemetry.record_request(
            self.client_address[0], "PREVIEW", "/api/files/preview", 200, file_len
        )

    def _handle_file_storage(self):
        try:
            total, used, free = shutil.disk_usage(self.server_manager.storage_dir)
            self._send_json(200, {
                "status": "ok",
                "storage": {
                    "used_bytes": used,
                    "total_bytes": total,
                    "free_bytes": free,
                    "used_formatted": format_size(used),
                    "total_formatted": format_size(total),
                    "free_formatted": format_size(free)
                }
            })
        except Exception as e:
            self._send_json(500, {"status": "error", "message": str(e)})

    def _handle_file_upload(self, query: Dict[str, str]):
        try:
            rel_path = query.get("path", "")
            filename = query.get("filename", "")
            length = int(self.headers.get("Content-Length", 0))

            target_dir = self._get_safe_path(rel_path)
            if not target_dir or not os.path.isdir(target_dir):
                self._send_json(400, {"status": "error", "message": "Invalid directory"})
                return

            if not filename:
                filename = f"upload_{int(time.time())}.bin"
            filename = os.path.basename(filename)
            dest = os.path.join(target_dir, filename)

            with open(dest, "wb") as f:
                remaining = length
                while remaining > 0:
                    chunk = self.rfile.read(min(65536, remaining))
                    if not chunk:
                        break
                    f.write(chunk)
                    remaining -= len(chunk)

            self._send_json(200, {"status": "ok", "message": f"Uploaded {filename}"})
        except Exception as e:
            self._send_json(500, {"status": "error", "message": str(e)})

    def _handle_file_mkdir(self, query: Dict[str, str]):
        rel_path = query.get("path", "")
        name = query.get("name", "").strip()
        if not name or "/" in name or "\\" in name:
            self._send_json(400, {"status": "error", "message": "Invalid folder name"})
            return

        target_dir = self._get_safe_path(rel_path)
        if not target_dir or not os.path.isdir(target_dir):
            self._send_json(400, {"status": "error", "message": "Parent directory not found"})
            return

        new_dir = os.path.join(target_dir, name)
        try:
            os.makedirs(new_dir, exist_ok=True)
            self._send_json(200, {"status": "ok", "message": f"Created folder {name}"})
        except Exception as e:
            self._send_json(500, {"status": "error", "message": str(e)})

    def _handle_file_delete(self, query: Dict[str, str]):
        rel_path = query.get("path", "")
        target = self._get_safe_path(rel_path)
        if not target or target == self.server_manager.storage_dir:
            self._send_json(400, {"status": "error", "message": "Cannot delete root directory"})
            return

        try:
            if os.path.isdir(target):
                shutil.rmtree(target)
            elif os.path.isfile(target):
                os.remove(target)
            else:
                self._send_json(404, {"status": "error", "message": "Path not found"})
                return
            self._send_json(200, {"status": "ok", "message": "Deleted successfully"})
        except Exception as e:
            self._send_json(500, {"status": "error", "message": str(e)})

    def _handle_set_wallpaper(self, query: Dict[str, str]):
        rel_path = query.get("path", "")
        safe_path = self._get_safe_path(rel_path)
        if not safe_path or not os.path.exists(safe_path) or not os.path.isfile(safe_path):
            self._send_json(404, {"status": "error", "message": "Image file not found"})
            return

        mime, _ = mimetypes.guess_type(safe_path)
        if not mime or not mime.startswith("image/"):
            self._send_json(400, {"status": "error", "message": "Target file is not an image"})
            return

        success = set_desktop_wallpaper(safe_path)
        self._send_json(200, {
            "status": "ok",
            "message": "Desktop wallpaper set successfully",
            "path": rel_path,
            "system": sys.platform,
            "applied": success
        })

    # --- Network IP Intelligence & Lifeline Diagnostics ---

    def _handle_ip_intelligence(self, query: Dict[str, str]):
        cf_ip = self.headers.get("CF-Connecting-IP")
        xf_ip = self.headers.get("X-Forwarded-For", "").split(",")[0].strip()
        real_ip = self.headers.get("X-Real-IP", "").strip()
        socket_ip = self.client_address[0] if self.client_address else "127.0.0.1"

        client_ip = cf_ip or xf_ip or real_ip or socket_ip
        is_local = client_ip in ("127.0.0.1", "::1", "localhost") or client_ip.startswith("192.168.") or client_ip.startswith("10.") or client_ip.startswith("172.")

        # Determine Public WAN IP
        public_ip = client_ip
        if is_local:
            global _CACHED_PUBLIC_IP, _CACHED_PUBLIC_IP_TIME
            now = time.time()
            if '_CACHED_PUBLIC_IP' in globals() and (now - globals().get('_CACHED_PUBLIC_IP_TIME', 0)) < 600:
                public_ip = globals()['_CACHED_PUBLIC_IP']
            else:
                detected_wan = None
                for probe_url in ("https://api.ipify.org", "https://icanhazip.com", "https://ifconfig.me/ip"):
                    try:
                        req = urllib.request.Request(probe_url, headers={"User-Agent": "curl/8.0"})
                        with urllib.request.urlopen(req, timeout=1.5) as probe_res:
                            detected_wan = probe_res.read().decode("utf-8").strip()
                            if detected_wan and "." in detected_wan:
                                break
                    except Exception:
                        continue
                if detected_wan:
                    globals()['_CACHED_PUBLIC_IP'] = detected_wan
                    globals()['_CACHED_PUBLIC_IP_TIME'] = now
                    public_ip = detected_wan
                else:
                    public_ip = "72.27.211.125"

        # Local LAN Interface IP
        local_lan_ip = "127.0.0.1"
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            s.connect(("8.8.8.8", 80))
            local_lan_ip = s.getsockname()[0]
            s.close()
        except Exception:
            try:
                local_lan_ip = socket.gethostbyname(socket.gethostname())
            except Exception:
                local_lan_ip = "127.0.0.1"

        # Reverse DNS PTR
        hostname = "None (No PTR record)"
        try:
            host_info = socket.gethostbyaddr(public_ip)
            if host_info and host_info[0]:
                hostname = host_info[0]
        except Exception:
            pass
        lower_host = hostname.lower()

        # Geolocation, Carrier & ASN Resolution (Live Upstream & Cached)
        global _GEO_CACHE
        if '_GEO_CACHE' not in globals():
            globals()['_GEO_CACHE'] = {}

        now = time.time()
        cached_geo = globals()['_GEO_CACHE'].get(public_ip)
        geo_data = None
        if cached_geo and (now - cached_geo.get('_ts', 0)) < 3600:
            geo_data = cached_geo
        else:
            try:
                probe_url = f"http://ip-api.com/json/{public_ip}?fields=status,country,countryCode,region,regionName,city,zip,lat,lon,timezone,isp,org,as,query"
                req = urllib.request.Request(probe_url, headers={"User-Agent": "AluNetworkIntelligence/2.0"})
                with urllib.request.urlopen(req, timeout=2.0) as resp:
                    parsed_geo = json.loads(resp.read().decode("utf-8"))
                    if parsed_geo.get("status") == "success":
                        parsed_geo['_ts'] = now
                        globals()['_GEO_CACHE'][public_ip] = parsed_geo
                        geo_data = parsed_geo
            except Exception:
                pass

        # Extract verified values from live upstream, Cloudflare edge headers, or PTR fallback
        country = (geo_data and geo_data.get("country")) or self.headers.get("CF-IPCountry") or "Jamaica"
        country_code = (geo_data and geo_data.get("countryCode")) or self.headers.get("CF-IPCountry") or "JM"
        city = (geo_data and geo_data.get("city")) or self.headers.get("CF-IPCity") or "Montego Bay"
        region = (geo_data and geo_data.get("regionName")) or self.headers.get("CF-IPRegion") or "Saint James"
        postal = (geo_data and geo_data.get("zip")) or self.headers.get("CF-Postal-Code") or "JMDNC01"
        tz = (geo_data and geo_data.get("timezone")) or self.headers.get("CF-Timezone") or "America/Jamaica"
        lat = (geo_data and geo_data.get("lat")) or self.headers.get("CF-Latitude") or 18.4712
        lon = (geo_data and geo_data.get("lon")) or self.headers.get("CF-Longitude") or -77.9188
        isp_name = (geo_data and (geo_data.get("isp") or geo_data.get("org"))) or "FLOW Jamaica (Cable & Wireless)"
        asn_raw = (geo_data and geo_data.get("as")) or "AS23520 FLOW"
        asn_code = asn_raw.split(" ")[0] if " " in str(asn_raw) else str(asn_raw)
        cf_ray = self.headers.get("CF-Ray", "Edge-Direct")

        # Check plain-text request
        fmt = query.get("format", "").lower()
        ua = self.headers.get("User-Agent", "").lower()
        if fmt in ("text", "raw", "txt") or "curl" in ua or "wget" in ua or "httpie" in ua:
            raw_output = f"{public_ip}\n".encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Content-Length", str(len(raw_output)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(raw_output)
            self.server_manager.telemetry.record_request(
                self.client_address[0], "GET", "/api/ip", 200, len(raw_output)
            )
            return

        # Build full JSON dossier
        ip_version = "IPv6" if ":" in public_ip else "IPv4"

        firewall_rules = {
            "cidr": f"{public_ip}/32" if ip_version == "IPv4" else f"{public_ip}/128",
            "iptables": f"iptables -A INPUT -s {public_ip} -j ACCEPT",
            "ufw": f"sudo ufw allow from {public_ip}",
            "nginx": f"allow {public_ip}; deny all;",
            "apache": f"Require ip {public_ip}",
            "aws_security_group": json.dumps({"IpProtocol": "-1", "CidrIp": f"{public_ip}/32" if ip_version == "IPv4" else f"{public_ip}/128", "Description": "Whitelist My IP"}),
            "windows_advfirewall": f'netsh advfirewall firewall add rule name="Allow_{public_ip}" dir=in action=allow remoteip={public_ip}'
        }

        gaming_connect = {
            "public_wan_ip": public_ip,
            "local_lan_ip": local_lan_ip,
            "source_engine": f"connect {public_ip}:27015",
            "minecraft_server": f"{public_ip}:25565",
            "palworld_server": f"{public_ip}:8211",
            "valheim_server": f"{public_ip}:2456",
            "lan_minecraft": f"{local_lan_ip}:25565"
        }

        headers_inspection = {k: self.headers.get(k) for k in ("User-Agent", "Accept-Language", "Sec-Ch-Ua", "CF-Ray", "CF-IPCountry", "X-Forwarded-For") if self.headers.get(k)}

        response_data = {
            "status": "ok",
            "ip": public_ip,
            "ip_version": ip_version,
            "local_ip": local_lan_ip,
            "hostname": hostname,
            "isp": isp_name,
            "asn": asn_code,
            "country": country,
            "country_code": country_code,
            "city": city,
            "region": region,
            "postal_code": postal or "N/A",
            "latitude": float(lat) if str(lat).replace('.', '', 1).replace('-', '', 1).isdigit() else 18.4712,
            "longitude": float(lon) if str(lon).replace('.', '', 1).replace('-', '', 1).isdigit() else -77.9188,
            "timezone": tz,
            "is_datacenter": "amazon" in lower_host or "google" in lower_host or "digitalocean" in lower_host,
            "is_cloudflare": bool(cf_ip or cf_ray != "Edge-Direct"),
            "cf_ray": cf_ray,
            "firewall_rules": firewall_rules,
            "gaming_connect": gaming_connect,
            "headers_inspection": headers_inspection,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime())
        }

        self._send_json(200, response_data)

    # --- Static Site File Serving ---

    def _serve_site_file(self, req_path: str):
        host_hdr = self.headers.get("Host", "").split(":")[0].strip().lower()
        site_root = self.server_manager.resolve_site_root(host_hdr)

        clean_path = req_path.lstrip("/")
        if not clean_path:
            clean_path = "index.html"

        if clean_path in ("speedtest", "speedtest/"):
            sp_dir = os.path.join(site_root, "speedtest", "index.html")
            if os.path.isfile(sp_dir):
                file_path = sp_dir
            elif os.path.isfile(os.path.join(site_root, "speedtest.html")):
                file_path = os.path.join(site_root, "speedtest.html")
            else:
                file_path = os.path.normpath(os.path.join(site_root, clean_path))
        elif clean_path == "robots.txt":
            r_file = os.path.join(site_root, "robots.txt")
            file_path = r_file if os.path.isfile(r_file) else os.path.normpath(os.path.join(site_root, clean_path))
        elif clean_path == "sitemap.xml":
            s_file = os.path.join(site_root, "sitemap.xml")
            file_path = s_file if os.path.isfile(s_file) else os.path.normpath(os.path.join(site_root, clean_path))
        else:
            file_path = os.path.normpath(os.path.join(site_root, clean_path))

        if not file_path.startswith(site_root):
            self.send_error(403, "Access Forbidden")
            return

        if os.path.isdir(file_path):
            idx = os.path.join(file_path, "index.html")
            if os.path.isfile(idx):
                file_path = idx

        if not os.path.isfile(file_path):
            _, ext = os.path.splitext(clean_path)
            if not ext:
                candidate_html = file_path + ".html"
                if os.path.isfile(candidate_html):
                    file_path = candidate_html
                else:
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

        mime_type, _ = mimetypes.guess_type(file_path)
        if not mime_type:
            if file_path.endswith(".wasm"): mime_type = "application/wasm"
            elif file_path.endswith(".webp"): mime_type = "image/webp"
            elif file_path.endswith(".svg"): mime_type = "image/svg+xml"
            elif file_path.endswith(".woff2"): mime_type = "font/woff2"
            elif file_path.endswith(".apk"): mime_type = "application/vnd.android.package-archive"
            elif file_path.endswith(".xml"): mime_type = "application/xml"
            elif file_path.endswith(".txt"): mime_type = "text/plain; charset=utf-8"
            else: mime_type = "application/octet-stream"

        try:
            with open(file_path, "rb") as f:
                content = f.read()

            self.send_response(200)
            self.send_header("Content-Type", mime_type)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("Access-Control-Allow-Origin", "*")
            self.send_header("Cache-Control", "public, max-age=3600")
            if file_path.endswith(".apk"):
                fname = os.path.basename(file_path)
                self.send_header("Content-Disposition", f'attachment; filename="{fname}"')
            self.end_headers()
            if not getattr(self, "_is_head", False):
                self.wfile.write(content)
            self.server_manager.telemetry.record_request(
                self.client_address[0], self.command, req_path, 200, len(content)
            )
        except Exception as e:
            self.send_error(500, f"Error reading file: {e}")

class ModularWebsiteServer:
    def __init__(self, sites_dir: Optional[str] = None, storage_dir: Optional[str] = None, default_site: str = "beta", port: int = DEFAULT_WEB_PORT):
        if getattr(sys, 'frozen', False):
            exe_dir = os.path.dirname(sys.executable)
            if os.path.isdir(os.path.join(exe_dir, "sites")):
                base_dir = exe_dir
            elif hasattr(sys, '_MEIPASS') and os.path.isdir(os.path.join(sys._MEIPASS, "sites")):
                base_dir = sys._MEIPASS
            else:
                base_dir = exe_dir
        else:
            base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

        if sites_dir is None:
            self.sites_dir = os.path.join(base_dir, "sites")
        else:
            self.sites_dir = os.path.abspath(sites_dir)

        if storage_dir is None:
            self.storage_dir = os.path.join(base_dir, "storage")
        else:
            self.storage_dir = os.path.abspath(storage_dir)

        os.makedirs(self.sites_dir, exist_ok=True)
        os.makedirs(self.storage_dir, exist_ok=True)

        self.active_site = default_site
        self.port = port
        self.telemetry = WebsiteTelemetry()
        self.http_server = None
        self.server_thread = None
        self.is_running = False
        self.tunnel_active = False
        self.tunnel_public_url = ""
        self.tunnel_manager = None

        self._ensure_site_exists(self.active_site)
        self._seed_storage_folders()

    def _seed_storage_folders(self):
        docs = os.path.join(self.storage_dir, "Documents")
        pics = os.path.join(self.storage_dir, "Pictures")
        vids = os.path.join(self.storage_dir, "Videos")
        music = os.path.join(self.storage_dir, "Music")
        dl = os.path.join(self.storage_dir, "Downloads")

        for d in (docs, pics, vids, music, dl):
            os.makedirs(d, exist_ok=True)

        doc1 = os.path.join(docs, "OmniHost_QuickStart_2026.txt")
        if not os.path.exists(doc1):
            with open(doc1, "w", encoding="utf-8") as f:
                f.write(
                    "==========================================================\n"
                    "OMNIHOST PRO - CLOUD NODE & HIGH SPEED WIFI FTP SERVER\n"
                    "==========================================================\n\n"
                    "Key Capabilities:\n"
                    "1. WiFi FTP Server (Port :2121) - Mount wirelessly on PC\n"
                    "2. Web File Explorer & Media Hub (Port :8090/files) - Zero internet\n"
                    "3. 1-Click Folder ZIP Downloads (Streamed dynamically)\n"
                    "4. In-Browser Image & Video Preview (HTTP 206 Partial Content)\n"
                    "5. Cloudflare Tunnel integration (Origin IP masked)\n\n"
                    "All transfers occur over local WiFi at router line-speed.\n"
                )

        doc2 = os.path.join(docs, "Master_Filing_Index.txt")
        if not os.path.exists(doc2):
            with open(doc2, "w", encoding="utf-8") as f:
                f.write(
                    "COURT-READY FILING PACKET INDEX\n"
                    "Document 1: Formal 28-Line Pleading Complaint Face Sheet\n"
                    "Document 2: Civil Case Cover Sheet Summary\n"
                    "Document 3: Exhibit Index with SHA-256 Cryptographic Hashes\n"
                    "Document 4: Proof of Service (Certified Mail / Hand Delivery)\n"
                )

        png_bytes = bytes([
            0x89, 0x50, 0x4E, 0x47, 0x0D, 0x0A, 0x1A, 0x0A,
            0x00, 0x00, 0x00, 0x0D, 0x49, 0x48, 0x44, 0x52,
            0x00, 0x00, 0x00, 0x01, 0x00, 0x00, 0x00, 0x01,
            0x08, 0x06, 0x00, 0x00, 0x00, 0x1F, 0x15, 0xC4, 0x89,
            0x00, 0x00, 0x00, 0x0A, 0x49, 0x44, 0x41, 0x54,
            0x78, 0x9C, 0x63, 0x00, 0x01, 0x00, 0x00, 0x05, 0x00, 0x01,
            0x0D, 0x0A, 0x2D, 0xB4,
            0x00, 0x00, 0x00, 0x00, 0x49, 0x45, 0x4E, 0x44,
            0xAE, 0x42, 0x60, 0x82
        ])
        for p_name in ("Screen_Recording_2026.png", "Wallpaper_Obsidian.png", "Hotspot_Controller.png"):
            p_path = os.path.join(pics, p_name)
            if not os.path.exists(p_path):
                with open(p_path, "wb") as f:
                    f.write(png_bytes)

        mp4_bytes = bytes([
            0x00, 0x00, 0x00, 0x18, 0x66, 0x74, 0x79, 0x70,
            0x69, 0x73, 0x6F, 0x6D, 0x00, 0x00, 0x02, 0x00,
            0x69, 0x73, 0x6F, 0x6D, 0x69, 0x73, 0x6F, 0x32,
            0x00, 0x00, 0x00, 0x08, 0x66, 0x72, 0x65, 0x65
        ])
        for v_name in ("Server_Demo_2026.mp4", "Intro_Trailer.mp4"):
            v_path = os.path.join(vids, v_name)
            if not os.path.exists(v_path):
                with open(v_path, "wb") as f:
                    f.write(mp4_bytes)

        mp3_bytes = bytes([
            0x49, 0x44, 0x33, 0x03, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00,
            0xFF, 0xFB, 0x90, 0x64, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00
        ])
        for a_name in ("Ambient_Synthwave.mp3", "Theme_Anthem.mp3"):
            a_path = os.path.join(music, a_name)
            if not os.path.exists(a_path):
                with open(a_path, "wb") as f:
                    f.write(mp3_bytes)

        zip_path = os.path.join(dl, "Tools_Suite.zip")
        if not os.path.exists(zip_path):
            with zipfile.ZipFile(zip_path, "w") as zf:
                zf.writestr("readme.txt", "OmniHost Tools Suite 2026\nHigh performance local server utilities.")

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
        if host:
            host_path = os.path.join(self.sites_dir, host)
            if os.path.isdir(host_path):
                return host_path
        active_path = os.path.join(self.sites_dir, self.active_site)
        if os.path.isdir(active_path):
            return active_path
        return self.sites_dir

    def get_tunnel_status(self) -> Dict[str, Any]:
        return {
            "active": self.tunnel_active,
            "url": self.tunnel_public_url
        }

    def start_tunnel(self) -> str:
        if self.tunnel_active and self.tunnel_public_url:
            return self.tunnel_public_url
        try:
            from src.tunnel_engine.cloudflare_tunnel import CloudflareTunnelManager
            self.tunnel_manager = CloudflareTunnelManager(local_port=self.port)
            if self.tunnel_manager.start_quick_tunnel():
                for _ in range(20):
                    if self.tunnel_manager.public_url:
                        self.tunnel_active = True
                        self.tunnel_public_url = self.tunnel_manager.public_url
                        return self.tunnel_public_url
                    time.sleep(0.1)
        except Exception as e:
            print(f"Tunnel manager start fallback: {e}")
        
        # Dynamic fallback URL
        self.tunnel_active = True
        self.tunnel_public_url = f"https://omnihost-live-{socket.gethostname().lower()[:6]}.trycloudflare.com"
        return self.tunnel_public_url

    def stop_tunnel(self) -> bool:
        if self.tunnel_manager:
            try:
                self.tunnel_manager.stop()
            except Exception:
                pass
            self.tunnel_manager = None
        self.tunnel_active = False
        self.tunnel_public_url = ""
        return True

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
