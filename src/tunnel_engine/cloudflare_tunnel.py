# ==============================================================================
# OmniHost Pro - Cloudflare Encrypted Outbound Tunnel Engine
# Reaches outbound to Cloudflare Anycast edge network to establish an encrypted tunnel.
# Hides Real Home IP, Zero Port-Forwarding, Free trycloudflare.com & Custom Domain Support
# ==============================================================================

import os
import sys
import re
import time
import shutil
import subprocess
import threading
from typing import Dict, Any, Optional, Callable

TRYCLOUDFLARE_REGEX = re.compile(r"https://[a-zA-Z0-9-]+\.trycloudflare\.com")

class CloudflareTunnelManager:
    def __init__(self, local_port: int = 8090, binary_path: Optional[str] = None,
                 on_url_ready: Optional[Callable[[str], None]] = None,
                 on_log: Optional[Callable[[str], None]] = None):
        self.local_port = local_port
        self.binary_path = binary_path or self._discover_binary()
        self.on_url_ready = on_url_ready
        self.on_log = on_log

        self.process: Optional[subprocess.Popen] = None
        self.public_url: Optional[str] = None
        self.is_connected = False
        self.monitor_thread: Optional[threading.Thread] = None
        self.token: Optional[str] = None

    def _discover_binary(self) -> str:
        # Check bundled bin directory
        local_bin = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "bin", "cloudflared.exe")
        if os.path.exists(local_bin):
            return local_bin

        # Check Finished_Products folder
        fp_bin = r"C:\Users\Alu\Documents\Finished_Products\cloudflared.exe"
        if os.path.exists(fp_bin):
            return fp_bin

        # Check system PATH
        which = shutil.which("cloudflared")
        if which:
            return which

        return "cloudflared.exe"

    def log(self, message: str):
        if self.on_log:
            self.on_log(message)

    def start_quick_tunnel(self) -> bool:
        """Starts a zero-configuration ephemeral Cloudflare tunnel on trycloudflare.com."""
        if self.is_connected:
            return True

        if not os.path.exists(self.binary_path):
            self.log(f"[ERROR] cloudflared binary not found at: {self.binary_path}")
            return False

        cmd = [
            self.binary_path,
            "tunnel",
            "--url", f"http://127.0.0.1:{self.local_port}",
            "--no-autoupdate"
        ]

        self.log(f"[TUNNEL] Launching outbound encrypted tunnel to Cloudflare Edge...")
        return self._launch_process(cmd)

    def start_token_tunnel(self, token: str) -> bool:
        """Starts a persistent custom domain Cloudflare tunnel using a tunnel token."""
        if self.is_connected:
            return True

        if not os.path.exists(self.binary_path):
            self.log(f"[ERROR] cloudflared binary not found at: {self.binary_path}")
            return False

        self.token = token.strip()
        cmd = [
            self.binary_path,
            "tunnel",
            "run",
            "--token", self.token
        ]

        self.log(f"[TUNNEL] Launching custom domain tunnel with token authentication...")
        return self._launch_process(cmd)

    def _launch_process(self, cmd: list) -> bool:
        try:
            # Creation flags to hide console window on Windows
            startupinfo = None
            creationflags = 0
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                startupinfo=startupinfo,
                creationflags=creationflags
            )

            self.is_connected = True
            self.monitor_thread = threading.Thread(target=self._monitor_output, daemon=True, name="CFTunnelMonitor")
            self.monitor_thread.start()
            return True

        except Exception as e:
            self.log(f"[ERROR] Failed to launch cloudflared: {e}")
            self.is_connected = False
            return False

    def _monitor_output(self):
        while self.is_connected and self.process and self.process.poll() is None:
            line = self.process.stdout.readline()
            if not line:
                break
            clean_line = line.strip()
            if not clean_line:
                continue

            # Check for trycloudflare.com URL
            match = TRYCLOUDFLARE_REGEX.search(clean_line)
            if match and not self.public_url:
                self.public_url = match.group(0)
                self.log(f"[SHIELD ACTIVE] Real Home IP Masked! Cloudflare Tunnel Live: {self.public_url}")
                if self.on_url_ready:
                    self.on_url_ready(self.public_url)

            # Filter relevant log lines
            if "Registered tunnel connection" in clean_line:
                self.log("[TUNNEL] Edge connection registered with Cloudflare Anycast server.")
            elif "Connection" in clean_line and "registered" in clean_line:
                self.log(f"[TUNNEL] {clean_line}")

        self.is_connected = False
        self.public_url = None
        self.log("[TUNNEL] Cloudflare tunnel process terminated.")

    def stop(self):
        """Terminates the Cloudflare tunnel process cleanly."""
        self.is_connected = False
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=3)
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None
        self.public_url = None
        self.log("[TUNNEL] Encrypted tunnel closed. Home IP returned to private state.")

if __name__ == "__main__":
    def print_url(url):
        print(f"\n>>> PUBLIC HTTPS URL IS READY: {url}\n")

    def print_log(msg):
        print(f"[TUNNEL LOG] {msg}")

    manager = CloudflareTunnelManager(local_port=8090, on_url_ready=print_url, on_log=print_log)
    print("Testing Cloudflare Tunnel Manager...")
    if manager.start_quick_tunnel():
        try:
            for _ in range(15):
                time.sleep(1)
                if manager.public_url:
                    print(f"Captured: {manager.public_url}")
                    break
        finally:
            manager.stop()
            print("Tunnel manager stopped cleanly.")
