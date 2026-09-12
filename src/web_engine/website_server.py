# ==============================================================================
# OmniHost Pro - Modular Website Engine
# Multi-Site Manager, Drop-in Static/SPA Hosting, Host Header Routing & Telemetry
# Full Web File Explorer & Media Hub Backend (Video Streaming, On-the-fly ZIP)
# ==============================================================================

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
from urllib.parse import urlparse, parse_qs, unquote
from http.server import ThreadingHTTPServer, BaseHTTPRequestHandler
from typing import Dict, List, Any, Optional

DEFAULT_WEB_PORT = 8090

def format_size(bytes_val: int) -> str:
    if bytes_val < 1024:
        return f"{bytes_val} B"
    elif bytes_val < 1024 * 1024:
        return f"{bytes_val / 1024:.1f} KB"
    elif bytes_val < 1024 * 1024 * 1024:
        return f"{bytes_val / (1024 * 1024):.1f} MB"
    else:
        return f"{bytes_val / (1024 * 1024 * 1024):.2f} GB"

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
        self.send_header("Access-Control-Allow-Methods", "GET, POST, DELETE, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type, Range")
        self.end_headers()

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

        # 3. Serve static site file
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

    # --- Static Site File Serving ---

    def _serve_site_file(self, req_path: str):
        host_hdr = self.headers.get("Host", "").split(":")[0].strip().lower()
        site_root = self.server_manager.resolve_site_root(host_hdr)

        clean_path = req_path.lstrip("/")
        if not clean_path:
            clean_path = "index.html"

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
    def __init__(self, sites_dir: Optional[str] = None, storage_dir: Optional[str] = None, default_site: str = "default", port: int = DEFAULT_WEB_PORT):
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
