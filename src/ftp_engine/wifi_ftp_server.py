# ==============================================================================
# OmniHost Pro - WiFi FTP Server Engine (RFC 959 Compliant)
# Resolves all issues of the 2.4-star Google Play "WiFi FTP Server" app:
# Custom Mount Point, One-Click Start/Stop, Anonymous/Auth Toggle, LAN IP Autodetect
# ==============================================================================

import os
import sys
import time
import socket
import logging
import threading
from typing import Dict, Any, Optional, Callable

from pyftpdlib.authorizers import DummyAuthorizer
from pyftpdlib.handlers import FTPHandler
from pyftpdlib.servers import FTPServer

DEFAULT_FTP_PORT = 2121

def get_lan_ip() -> str:
    """Detects the primary LAN IP address of this machine."""
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    try:
        # Doesn't need to be reachable, just triggers route lookup
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
    except Exception:
        ip = "127.0.0.1"
    finally:
        s.close()
    return ip

class OmniFTPHandler(FTPHandler):
    event_callback: Optional[Callable[[str], None]] = None

    def on_connect(self):
        msg = f"[CONNECT] FTP client connected from {self.remote_ip}:{self.remote_port}"
        if OmniFTPHandler.event_callback:
            OmniFTPHandler.event_callback(msg)

    def on_disconnect(self):
        msg = f"[DISCONNECT] FTP client {self.remote_ip} disconnected"
        if OmniFTPHandler.event_callback:
            OmniFTPHandler.event_callback(msg)

    def on_login(self, username):
        msg = f"[AUTH] User '{username}' logged in successfully from {self.remote_ip}"
        if OmniFTPHandler.event_callback:
            OmniFTPHandler.event_callback(msg)

    def on_file_sent(self, file):
        msg = f"[DOWNLOAD] Completed: {os.path.basename(file)}"
        if OmniFTPHandler.event_callback:
            OmniFTPHandler.event_callback(msg)

    def on_file_received(self, file):
        msg = f"[UPLOAD] Completed: {os.path.basename(file)}"
        if OmniFTPHandler.event_callback:
            OmniFTPHandler.event_callback(msg)

class WiFiFTPServer:
    def __init__(self, mount_dir: str, port: int = DEFAULT_FTP_PORT,
                 allow_anonymous: bool = True, username: str = "admin",
                 password: str = "omnihost", log_callback: Optional[Callable[[str], None]] = None):
        self.mount_dir = os.path.abspath(mount_dir)
        os.makedirs(self.mount_dir, exist_ok=True)
        self.port = port
        self.allow_anonymous = allow_anonymous
        self.username = username
        self.password = password
        self.log_callback = log_callback
        self.server = None
        self.server_thread = None
        self.is_running = False

        OmniFTPHandler.event_callback = log_callback

    def set_mount_dir(self, new_dir: str):
        self.mount_dir = os.path.abspath(new_dir)
        os.makedirs(self.mount_dir, exist_ok=True)

    def get_connection_url(self) -> str:
        lan_ip = get_lan_ip()
        return f"ftp://{lan_ip}:{self.port}"

    def start(self):
        if self.is_running:
            return

        authorizer = DummyAuthorizer()

        # Permissions:
        # e = change directory
        # l = list files
        # r = retrieve file
        # a = append file
        # d = delete file
        # f = rename file
        # m = create directory
        # w = write file
        # M = change mode
        # T = change time
        perm_full = "elradfmwMT"
        perm_read = "elr"

        if self.allow_anonymous:
            # Grant full write access or read access
            authorizer.add_anonymous(self.mount_dir, perm=perm_full)
        else:
            authorizer.add_user(self.username, self.password, self.mount_dir, perm=perm_full)

        handler = OmniFTPHandler
        handler.authorizer = authorizer
        handler.banner = "OmniHost Pro High-Speed WiFi FTP Server Ready."
        handler.passive_ports = range(60000, 60050)

        # Silence raw pyftpdlib logging to console
        logging.getLogger("pyftpdlib").setLevel(logging.CRITICAL)

        self.server = FTPServer(("0.0.0.0", self.port), handler)
        self.server.max_cons = 256
        self.server.max_cons_per_ip = 20

        self.server_thread = threading.Thread(target=self._run_server, daemon=True, name="OmniFTPServerThread")
        self.server_thread.start()
        self.is_running = True

        if self.log_callback:
            self.log_callback(f"[STARTED] WiFi FTP Server listening on {self.get_connection_url()} (Mounted: {self.mount_dir})")

    def _run_server(self):
        try:
            self.server.serve_forever()
        except Exception:
            pass

    def stop(self):
        if not self.is_running:
            return
        self.is_running = False
        if self.server:
            try:
                self.server.close_all()
            except Exception:
                pass
        if self.log_callback:
            self.log_callback("[STOPPED] WiFi FTP Server has stopped.")

if __name__ == "__main__":
    def print_log(msg):
        print(f"[FTP LOG] {msg}")

    mount = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "sites", "default")
    ftp = WiFiFTPServer(mount_dir=mount, port=DEFAULT_FTP_PORT, allow_anonymous=True, log_callback=print_log)
    ftp.start()
    print(f"WiFi FTP Server started. Connect from any client: {ftp.get_connection_url()}")
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        ftp.stop()
        print("FTP stopped.")
