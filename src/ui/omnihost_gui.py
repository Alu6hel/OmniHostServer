# ==============================================================================
# OmniHost Pro - Commercial Desktop GUI Dashboard (Metro Live Tiles Edition)
# Integrated Modular Website Host, WiFi FTP Server & Cloudflare Encrypted Tunnel
# Features: Dynamic Metro Live Tiles Grid, Multi-Theme Engine, Real-Time Telemetry
# ==============================================================================

import os
import sys
import json
import time
import queue
import webbrowser
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox, filedialog

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.web_engine.website_server import ModularWebsiteServer, DEFAULT_WEB_PORT
from src.ftp_engine.wifi_ftp_server import WiFiFTPServer, DEFAULT_FTP_PORT, get_lan_ip
from src.tunnel_engine.cloudflare_tunnel import CloudflareTunnelManager
from src.domain_engine.domain_manager import DomainManager

THEMES = {
    "windows_metro": {
        "name": "Windows Metro (Modern Live Tiles)",
        "bg": "#0a1118", "surf": "#101d2d", "card": "#182c44",
        "accent": "#00A4EF", "blue": "#0078D7", "purple": "#7C3AED",
        "text": "#FFFFFF", "muted": "#94A3B8", "border": "#1f3b5c",
        "tile_web": "#008A00", "tile_ftp": "#0078D7", "tile_tunnel": "#6B21A8",
        "tile_telemetry": "#008299", "tile_site": "#D97706"
    },
    "fluent_dark": {
        "name": "Fluent Dark (Obsidian & Emerald)",
        "bg": "#080B11", "surf": "#111622", "card": "#182030",
        "accent": "#10B981", "blue": "#3B82F6", "purple": "#8B5CF6",
        "text": "#F8FAFC", "muted": "#94A3B8", "border": "#222D42",
        "tile_web": "#059669", "tile_ftp": "#2563EB", "tile_tunnel": "#7C3AED",
        "tile_telemetry": "#0891B2", "tile_site": "#D97706"
    },
    "cyberpunk_neon": {
        "name": "Cyberpunk Neon (Cyan & Magenta)",
        "bg": "#0A0612", "surf": "#150C24", "card": "#22123B",
        "accent": "#06B6D4", "blue": "#F43F5E", "purple": "#C084FC",
        "text": "#FAF5FF", "muted": "#A855F7", "border": "#3B1861",
        "tile_web": "#059669", "tile_ftp": "#0284C7", "tile_tunnel": "#9333EA",
        "tile_telemetry": "#0891B2", "tile_site": "#E11D48"
    },
    "nord_frost": {
        "name": "Nord Frost (Arctic Deep Blue)",
        "bg": "#0F141C", "surf": "#1A2332", "card": "#243044",
        "accent": "#38BDF8", "blue": "#60A5FA", "purple": "#818CF8",
        "text": "#F0F9FF", "muted": "#94A3B8", "border": "#334155",
        "tile_web": "#059669", "tile_ftp": "#0284C7", "tile_tunnel": "#6366F1",
        "tile_telemetry": "#0284C7", "tile_site": "#D97706"
    },
    "midnight_gold": {
        "name": "Midnight Gold (Onyx & Amber)",
        "bg": "#0C0A06", "surf": "#1A160C", "card": "#262012",
        "accent": "#F59E0B", "blue": "#D97706", "purple": "#FBBF24",
        "text": "#FFFBEB", "muted": "#A1A1AA", "border": "#3D341D",
        "tile_web": "#059669", "tile_ftp": "#B45309", "tile_tunnel": "#7C3AED",
        "tile_telemetry": "#0F766E", "tile_site": "#D97706"
    },
    "monochrome_slate": {
        "name": "Monochrome Slate (Minimalist Studio)",
        "bg": "#121214", "surf": "#1C1C1F", "card": "#27272A",
        "accent": "#E4E4E7", "blue": "#A1A1AA", "purple": "#D4D4D8",
        "text": "#FFFFFF", "muted": "#71717A", "border": "#3F3F46",
        "tile_web": "#27272A", "tile_ftp": "#3F3F46", "tile_tunnel": "#52525B",
        "tile_telemetry": "#3F3F46", "tile_site": "#27272A"
    }
}

class OmniHostApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OmniHost Pro - Modular Website & WiFi FTP Cloud Server")
        self.geometry("1180x800")
        self.minsize(1020, 680)

        # Base directories resolution (checks frozen exe and disk)
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

        self.base_dir = base_dir
        self.settings_file = os.path.join(base_dir, "settings.json")
        self.active_theme_key = self._load_saved_theme()
        self._apply_palette(self.active_theme_key)

        self.configure(bg=self.c_bg)
        self.log_queue = queue.Queue()
        self.active_tab = "dashboard"

        # Core Engines - defaulting to "beta" (Alumungandr Suite)
        self.sites_dir = os.path.join(base_dir, "sites")
        self.web_server = ModularWebsiteServer(sites_dir=self.sites_dir, default_site="beta", port=DEFAULT_WEB_PORT)

        default_mount = os.path.join(self.sites_dir, "beta")
        if not os.path.exists(default_mount):
            default_mount = self.sites_dir

        self.ftp_server = WiFiFTPServer(
            mount_dir=default_mount,
            port=DEFAULT_FTP_PORT,
            allow_anonymous=True,
            log_callback=self._ftp_log_event
        )

        self.tunnel_manager = CloudflareTunnelManager(
            local_port=DEFAULT_WEB_PORT,
            on_url_ready=self._on_tunnel_url,
            on_log=self._tunnel_log_event
        )

        self.setup_ui()

        # Start Web and FTP servers by default
        self.web_server.start()
        self.ftp_server.start()

        self.after(200, self._process_log_queue)
        self.after(1500, self._refresh_telemetry)

    def _load_saved_theme(self) -> str:
        if os.path.exists(self.settings_file):
            try:
                with open(self.settings_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    th = data.get("theme", "windows_metro")
                    if th in THEMES:
                        return th
            except Exception:
                pass
        return "windows_metro"

    def _save_theme(self, theme_key: str):
        self.active_theme_key = theme_key
        data = {"theme": theme_key, "updated_at": time.time()}
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _apply_palette(self, theme_key: str):
        pal = THEMES.get(theme_key, THEMES["windows_metro"])
        self.c_bg = pal["bg"]
        self.c_surf = pal["surf"]
        self.c_card = pal["card"]
        self.c_accent = pal["accent"]
        self.c_blue = pal["blue"]
        self.c_purple = pal["purple"]
        self.c_text = pal["text"]
        self.c_muted = pal["muted"]
        self.c_border = pal["border"]
        self.c_tile_web = pal.get("tile_web", "#008A00")
        self.c_tile_ftp = pal.get("tile_ftp", "#0078D7")
        self.c_tile_tunnel = pal.get("tile_tunnel", "#6B21A8")
        self.c_tile_telemetry = pal.get("tile_telemetry", "#008299")
        self.c_tile_site = pal.get("tile_site", "#D97706")
        self.c_success = "#10B981"
        self.c_warn = "#F59E0B"
        self.c_danger = "#EF4444"

    def change_theme(self, theme_key: str):
        self._save_theme(theme_key)
        self._apply_palette(theme_key)
        self.configure(bg=self.c_bg)
        self.setup_ui()
        self.log(f"[SETTINGS] Theme switched to: {THEMES[theme_key]['name']}")

    def _ftp_log_event(self, msg: str):
        self.log(f"[FTP] {msg}")

    def _tunnel_log_event(self, msg: str):
        self.log(f"{msg}")

    def _on_tunnel_url(self, url: str):
        if hasattr(self, "card_cf_val") and self.card_cf_val.winfo_exists():
            self.card_cf_val.configure(text=url)
        if hasattr(self, "lbl_shield_status") and self.lbl_shield_status.winfo_exists():
            self.lbl_shield_status.configure(text="● REAL IP MASKED (Cloudflare Edge)", fg="#10B981")
        if hasattr(self, "lbl_metro_tunnel_status") and self.lbl_metro_tunnel_status.winfo_exists():
            self.lbl_metro_tunnel_status.configure(text="● EDGE CONNECTED", fg="#A7F3D0")
        self.log(f"[SHIELD] Public HTTPS Route Active: {url}")

    def setup_ui(self):
        for w in self.winfo_children():
            w.destroy()

        # Top Navigation & Metro Branding Banner
        top_bar = tk.Frame(self, bg=self.c_surf, height=64)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        top_bar.pack_propagate(False)

        brand = tk.Frame(top_bar, bg=self.c_surf)
        brand.pack(side=tk.LEFT, padx=18, pady=10)

        tk.Label(brand, text="⊞ OMNIHOST PRO", font=("Segoe UI", 14, "bold"), fg=self.c_accent, bg=self.c_surf).pack(anchor="w")
        tk.Label(brand, text="Modular Web Server & Metro WiFi FTP Cloud Hub", font=("Segoe UI", 8), fg=self.c_muted, bg=self.c_surf).pack(anchor="w")

        # Metro Navigation Tabs in Header
        tab_frame = tk.Frame(top_bar, bg=self.c_surf)
        tab_frame.pack(side=tk.LEFT, padx=16)

        tabs = [
            ("dashboard", "Dashboard"),
            ("sites", "Sites"),
            ("ftp", "WiFi FTP"),
            ("tunnel", "Tunnel"),
            ("settings", "⚙ Settings & Themes")
        ]
        for tid, tname in tabs:
            act = (tid == self.active_tab)
            bg = self.c_accent if act else self.c_card
            fg = "#000000" if act else self.c_text
            tk.Button(
                tab_frame, text=tname, font=("Segoe UI", 9, "bold" if act else "normal"),
                bg=bg, fg=fg, bd=0, padx=14, pady=6, cursor="hand2",
                command=lambda t=tid: self.set_tab(t)
            ).pack(side=tk.LEFT, padx=3)

        # Tunnel Shield Status Indicator Pill
        t_connected = getattr(self, "tunnel_manager", None) and self.tunnel_manager.is_connected
        s_text = "● REAL IP MASKED (Cloudflare Edge)" if t_connected else "○ Tunnel Standby"
        s_color = self.c_success if t_connected else self.c_muted
        self.lbl_shield_status = tk.Label(top_bar, text=s_text, font=("Segoe UI", 9, "bold"), fg=s_color, bg=self.c_card, padx=14, pady=6)
        self.lbl_shield_status.pack(side=tk.RIGHT, padx=18, pady=16)

        # Main Dynamic Content Frame
        self.content = tk.Frame(self, bg=self.c_bg)
        self.content.pack(fill=tk.BOTH, expand=True, padx=16, pady=(10, 16))

        if self.active_tab == "dashboard":
            self.view_dashboard()
        elif self.active_tab == "sites":
            self.view_sites()
        elif self.active_tab == "ftp":
            self.view_ftp()
        elif self.active_tab == "tunnel":
            self.view_tunnel()
        elif self.active_tab == "settings":
            self.view_settings()

    def set_tab(self, tab_id: str):
        self.active_tab = tab_id
        self.setup_ui()

    def copy_to_clipboard(self, text: str):
        self.clipboard_clear()
        self.clipboard_append(text)
        self.log(f"[CLIPBOARD] Copied to clipboard: {text}")

    def open_cf_link(self):
        url = self.card_cf_val.cget("text")
        if url.startswith("https://"):
            webbrowser.open(url)

    # =========================================================================
    # VIEW: DASHBOARD (WINDOWS 8 METRO DYNAMIC LIVE TILES)
    # =========================================================================
    def view_dashboard(self):
        lan_ip = get_lan_ip()

        # ---------------------------------------------------------------------
        # 1. METRO DYNAMIC LIVE TILES GRID (Inspired by Windows 8 Start Screen)
        # ---------------------------------------------------------------------
        tiles_container = tk.Frame(self.content, bg=self.c_bg)
        tiles_container.pack(fill=tk.X, pady=(0, 12))

        # --- TILE 1: WEB ENGINE (Emerald Green Metro Tile) ---
        t1 = tk.Frame(tiles_container, bg=self.c_tile_web, padx=12, pady=10, relief=tk.FLAT)
        t1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        t1_top = tk.Frame(t1, bg=self.c_tile_web)
        t1_top.pack(fill=tk.X)
        tk.Label(t1_top, text="🌐 WEB ENGINE", font=("Segoe UI", 9, "bold"), fg="#D1FAE5", bg=self.c_tile_web).pack(side=tk.LEFT)
        self.lbl_metro_web_status = tk.Label(t1_top, text="● ONLINE", font=("Segoe UI", 8, "bold"), fg="#FFFFFF", bg=self.c_tile_web)
        self.lbl_metro_web_status.pack(side=tk.RIGHT)

        tk.Label(t1, text=f":{DEFAULT_WEB_PORT}", font=("Segoe UI", 22, "bold"), fg="#FFFFFF", bg=self.c_tile_web).pack(anchor="w", pady=(2, 0))
        self.card_web_val = tk.Label(t1, text=f"http://{lan_ip}:{DEFAULT_WEB_PORT}", font=("Consolas", 9, "bold"), fg="#ECFDF5", bg=self.c_tile_web)
        self.card_web_val.pack(anchor="w", pady=(1, 4))
        tk.Label(t1, text="Serving 12 Pages (Alumungandr Suite)", font=("Segoe UI", 7), fg="#D1FAE5", bg=self.c_tile_web).pack(anchor="w", pady=(0, 6))

        t1_btns = tk.Frame(t1, bg=self.c_tile_web)
        t1_btns.pack(fill=tk.X)
        tk.Button(t1_btns, text="↗ Open", font=("Segoe UI", 8, "bold"), bg="#065F46", fg="#FFFFFF", bd=0, padx=8, pady=3, cursor="hand2", command=lambda: webbrowser.open(f"http://localhost:{DEFAULT_WEB_PORT}")).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(t1_btns, text="📋 Copy", font=("Segoe UI", 8), bg="#065F46", fg="#D1FAE5", bd=0, padx=8, pady=3, cursor="hand2", command=lambda: self.copy_to_clipboard(f"http://{lan_ip}:{DEFAULT_WEB_PORT}")).pack(side=tk.LEFT, padx=(0, 4))
        self.btn_tile_web_toggle = tk.Button(t1_btns, text="■ Stop", font=("Segoe UI", 8), bg="#065F46", fg="#FECACA", bd=0, padx=8, pady=3, cursor="hand2", command=self.toggle_web)
        self.btn_tile_web_toggle.pack(side=tk.LEFT)

        # --- TILE 2: WIFI FTP CLOUD (Cobalt Blue Metro Tile) ---
        t2 = tk.Frame(tiles_container, bg=self.c_tile_ftp, padx=12, pady=10, relief=tk.FLAT)
        t2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        t2_top = tk.Frame(t2, bg=self.c_tile_ftp)
        t2_top.pack(fill=tk.X)
        tk.Label(t2_top, text="📁 WIFI FTP CLOUD", font=("Segoe UI", 9, "bold"), fg="#DBEAFE", bg=self.c_tile_ftp).pack(side=tk.LEFT)
        self.lbl_metro_ftp_status = tk.Label(t2_top, text="● READY", font=("Segoe UI", 8, "bold"), fg="#FFFFFF", bg=self.c_tile_ftp)
        self.lbl_metro_ftp_status.pack(side=tk.RIGHT)

        tk.Label(t2, text=f":{DEFAULT_FTP_PORT}", font=("Segoe UI", 22, "bold"), fg="#FFFFFF", bg=self.c_tile_ftp).pack(anchor="w", pady=(2, 0))
        self.card_ftp_val = tk.Label(t2, text=f"ftp://{lan_ip}:{DEFAULT_FTP_PORT}", font=("Consolas", 9, "bold"), fg="#EFF6FF", bg=self.c_tile_ftp)
        self.card_ftp_val.pack(anchor="w", pady=(1, 4))
        mount_name = os.path.basename(self.ftp_server.mount_dir)
        tk.Label(t2, text=f"Mounted: sites/{mount_name}", font=("Segoe UI", 7), fg="#DBEAFE", bg=self.c_tile_ftp).pack(anchor="w", pady=(0, 6))

        t2_btns = tk.Frame(t2, bg=self.c_tile_ftp)
        t2_btns.pack(fill=tk.X)
        tk.Button(t2_btns, text="📋 Copy FTP", font=("Segoe UI", 8, "bold"), bg="#1E40AF", fg="#FFFFFF", bd=0, padx=8, pady=3, cursor="hand2", command=lambda: self.copy_to_clipboard(f"ftp://{lan_ip}:{DEFAULT_FTP_PORT}")).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(t2_btns, text="📂 Mount", font=("Segoe UI", 8), bg="#1E40AF", fg="#DBEAFE", bd=0, padx=8, pady=3, cursor="hand2", command=self.open_mount_folder).pack(side=tk.LEFT, padx=(0, 4))
        self.btn_tile_ftp_toggle = tk.Button(t2_btns, text="■ Stop", font=("Segoe UI", 8), bg="#1E40AF", fg="#FECACA", bd=0, padx=8, pady=3, cursor="hand2", command=self.toggle_ftp)
        self.btn_tile_ftp_toggle.pack(side=tk.LEFT)

        # --- TILE 3: CLOUDFLARE SHIELDED TUNNEL (Royal Purple Metro Tile) ---
        t3 = tk.Frame(tiles_container, bg=self.c_tile_tunnel, padx=12, pady=10, relief=tk.FLAT)
        t3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        t3_top = tk.Frame(t3, bg=self.c_tile_tunnel)
        t3_top.pack(fill=tk.X)
        tk.Label(t3_top, text="🛡️ EDGE TUNNEL", font=("Segoe UI", 9, "bold"), fg="#F3E8FF", bg=self.c_tile_tunnel).pack(side=tk.LEFT)
        self.lbl_metro_tunnel_status = tk.Label(t3_top, text="○ STANDBY", font=("Segoe UI", 8, "bold"), fg="#E9D5FF", bg=self.c_tile_tunnel)
        self.lbl_metro_tunnel_status.pack(side=tk.RIGHT)

        tk.Label(t3, text="HTTPS", font=("Segoe UI", 22, "bold"), fg="#FFFFFF", bg=self.c_tile_tunnel).pack(anchor="w", pady=(2, 0))
        self.card_cf_val = tk.Label(t3, text="https://... (Click 'Start')", font=("Consolas", 8, "bold"), fg="#FAF5FF", bg=self.c_tile_tunnel)
        self.card_cf_val.pack(anchor="w", pady=(1, 4))
        tk.Label(t3, text="Zero Router Port Forwarding", font=("Segoe UI", 7), fg="#E9D5FF", bg=self.c_tile_tunnel).pack(anchor="w", pady=(0, 6))

        t3_btns = tk.Frame(t3, bg=self.c_tile_tunnel)
        t3_btns.pack(fill=tk.X)
        self.btn_tile_tunnel_toggle = tk.Button(t3_btns, text="⚡ Start", font=("Segoe UI", 8, "bold"), bg="#581C87", fg="#FFFFFF", bd=0, padx=8, pady=3, cursor="hand2", command=self.toggle_tunnel)
        self.btn_tile_tunnel_toggle.pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(t3_btns, text="📋 Copy", font=("Segoe UI", 8), bg="#581C87", fg="#E9D5FF", bd=0, padx=8, pady=3, cursor="hand2", command=lambda: self.copy_to_clipboard(self.card_cf_val.cget("text"))).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(t3_btns, text="↗ Open", font=("Segoe UI", 8), bg="#581C87", fg="#E9D5FF", bd=0, padx=8, pady=3, cursor="hand2", command=self.open_cf_link).pack(side=tk.LEFT)

        # --- TILE 4: TELEMETRY & PERFORMANCE (Deep Cyan / Teal Metro Tile) ---
        t4 = tk.Frame(tiles_container, bg=self.c_tile_telemetry, padx=12, pady=10, relief=tk.FLAT)
        t4.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        t4_top = tk.Frame(t4, bg=self.c_tile_telemetry)
        t4_top.pack(fill=tk.X)
        tk.Label(t4_top, text="⚡ TELEMETRY", font=("Segoe UI", 9, "bold"), fg="#CCFBF1", bg=self.c_tile_telemetry).pack(side=tk.LEFT)
        tk.Label(t4_top, text="● LIVE", font=("Segoe UI", 8, "bold"), fg="#FFFFFF", bg=self.c_tile_telemetry).pack(side=tk.RIGHT)

        self.lbl_tile_qps = tk.Label(t4, text="0.0 QPS", font=("Segoe UI", 22, "bold"), fg="#FFFFFF", bg=self.c_tile_telemetry)
        self.lbl_tile_qps.pack(anchor="w", pady=(2, 0))
        self.lbl_tile_hits = tk.Label(t4, text="Total Hits: 0", font=("Consolas", 9, "bold"), fg="#E0F2FE", bg=self.c_tile_telemetry)
        self.lbl_tile_hits.pack(anchor="w", pady=(1, 4))
        self.lbl_tile_bytes = tk.Label(t4, text="Bandwidth: 0.0 KB", font=("Segoe UI", 7), fg="#CCFBF1", bg=self.c_tile_telemetry)
        self.lbl_tile_bytes.pack(anchor="w", pady=(0, 6))

        t4_btns = tk.Frame(t4, bg=self.c_tile_telemetry)
        t4_btns.pack(fill=tk.X)
        tk.Button(t4_btns, text="🔄 Reset", font=("Segoe UI", 8), bg="#134E4A", fg="#CCFBF1", bd=0, padx=8, pady=3, cursor="hand2", command=self.reset_telemetry).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(t4_btns, text="📋 Copy Stats", font=("Segoe UI", 8, "bold"), bg="#134E4A", fg="#FFFFFF", bd=0, padx=8, pady=3, cursor="hand2", command=self.copy_telemetry).pack(side=tk.LEFT)

        # --- TILE 5: ACTIVE SITE CONTAINER (Amber / Warm Gold Metro Tile) ---
        t5 = tk.Frame(tiles_container, bg=self.c_tile_site, padx=12, pady=10, relief=tk.FLAT)
        t5.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

        t5_top = tk.Frame(t5, bg=self.c_tile_site)
        t5_top.pack(fill=tk.X)
        tk.Label(t5_top, text="🚀 DEPLOY CONTAINER", font=("Segoe UI", 9, "bold"), fg="#FEF3C7", bg=self.c_tile_site).pack(side=tk.LEFT)
        tk.Label(t5_top, text="★ ACTIVE", font=("Segoe UI", 8, "bold"), fg="#FFFFFF", bg=self.c_tile_site).pack(side=tk.RIGHT)

        self.lbl_tile_site_name = tk.Label(t5, text=self.web_server.active_site.upper(), font=("Segoe UI", 22, "bold"), fg="#FFFFFF", bg=self.c_tile_site)
        self.lbl_tile_site_name.pack(anchor="w", pady=(2, 0))
        tk.Label(t5, text=f"Container: sites/{self.web_server.active_site}", font=("Consolas", 8, "bold"), fg="#FFFBEB", bg=self.c_tile_site).pack(anchor="w", pady=(1, 4))
        tk.Label(t5, text="12 Pages & 4 Native APKs", font=("Segoe UI", 7), fg="#FEF3C7", bg=self.c_tile_site).pack(anchor="w", pady=(0, 6))

        t5_btns = tk.Frame(t5, bg=self.c_tile_site)
        t5_btns.pack(fill=tk.X)
        tk.Button(t5_btns, text="🔄 Switch", font=("Segoe UI", 8, "bold"), bg="#78350F", fg="#FFFFFF", bd=0, padx=8, pady=3, cursor="hand2", command=lambda: self.set_tab("sites")).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(t5_btns, text="📂 Folder", font=("Segoe UI", 8), bg="#78350F", fg="#FEF3C7", bd=0, padx=8, pady=3, cursor="hand2", command=self.open_sites_folder).pack(side=tk.LEFT)

        # ---------------------------------------------------------------------
        # 2. SPLIT WORKSPACE: REAL-TIME TRAFFIC LOG (68%) & DIAGNOSTICS (32%)
        # ---------------------------------------------------------------------
        split = tk.Frame(self.content, bg=self.c_bg)
        split.pack(fill=tk.BOTH, expand=True)

        # Left Column: Terminal Traffic Log
        left = tk.Frame(split, bg=self.c_surf, highlightbackground=self.c_border, highlightthickness=1)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 8))

        log_hdr = tk.Frame(left, bg=self.c_surf)
        log_hdr.pack(fill=tk.X, padx=12, pady=8)
        tk.Label(log_hdr, text="REAL-TIME TRAFFIC & EVENT LOG", font=("Segoe UI", 10, "bold"), fg=self.c_text, bg=self.c_surf).pack(side=tk.LEFT)
        
        btn_clear = tk.Button(log_hdr, text="Clear Log", font=("Segoe UI", 8), bg=self.c_card, fg=self.c_muted, bd=0, padx=8, pady=2, cursor="hand2", command=self.clear_log)
        btn_clear.pack(side=tk.RIGHT, padx=4)

        self.log_text = tk.Text(left, bg="#05080E", fg="#CBD5E1", font=("Consolas", 9), bd=0, padx=12, pady=10, relief=tk.FLAT)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=10, pady=(0, 10))

        # Right Column: Diagnostics & Quick Controls Hub
        right = tk.Frame(split, bg=self.c_surf, width=320, highlightbackground=self.c_border, highlightthickness=1)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        tk.Label(right, text="SERVER CONTROLS", font=("Segoe UI", 10, "bold"), fg=self.c_text, bg=self.c_surf).pack(anchor="w", padx=14, pady=(12, 6))

        self.btn_toggle_web = tk.Button(
            right, text="■ Stop Web Server (:8090)", font=("Segoe UI", 9, "bold"),
            bg=self.c_card, fg=self.c_danger, bd=0, padx=12, pady=8, cursor="hand2",
            command=self.toggle_web
        )
        self.btn_toggle_web.pack(fill=tk.X, padx=14, pady=3)

        self.btn_toggle_ftp = tk.Button(
            right, text="■ Stop WiFi FTP Server (:2121)", font=("Segoe UI", 9, "bold"),
            bg=self.c_card, fg=self.c_danger, bd=0, padx=12, pady=8, cursor="hand2",
            command=self.toggle_ftp
        )
        self.btn_toggle_ftp.pack(fill=tk.X, padx=14, pady=3)

        self.btn_toggle_tunnel = tk.Button(
            right, text="⚡ Start Cloudflare Tunnel", font=("Segoe UI", 9, "bold"),
            bg=self.c_blue, fg="#FFFFFF", bd=0, padx=12, pady=8, cursor="hand2",
            command=self.toggle_tunnel
        )
        self.btn_toggle_tunnel.pack(fill=tk.X, padx=14, pady=3)

        tk.Label(right, text="SYSTEM NETWORK RADAR", font=("Segoe UI", 9, "bold"), fg=self.c_muted, bg=self.c_surf).pack(anchor="w", padx=14, pady=(16, 6))

        radar_box = tk.Frame(right, bg=self.c_card, padx=12, pady=10, highlightbackground=self.c_border, highlightthickness=1)
        radar_box.pack(fill=tk.X, padx=14, pady=3)

        tk.Label(radar_box, text=f"• Host Machine IP: {lan_ip}", font=("Consolas", 8), fg=self.c_accent, bg=self.c_card).pack(anchor="w", pady=1)
        tk.Label(radar_box, text=f"• HTTP Port: {DEFAULT_WEB_PORT} (Dual-Stack)", font=("Consolas", 8), fg=self.c_text, bg=self.c_card).pack(anchor="w", pady=1)
        tk.Label(radar_box, text=f"• FTP Port: {DEFAULT_FTP_PORT} (Passive/Active)", font=("Consolas", 8), fg=self.c_text, bg=self.c_card).pack(anchor="w", pady=1)
        tk.Label(radar_box, text=f"• Active Site: sites/{self.web_server.active_site}", font=("Consolas", 8), fg=self.c_muted, bg=self.c_card).pack(anchor="w", pady=1)
        tk.Label(radar_box, text="• Encryption: TLS 1.3 / Cloudflare Anycast", font=("Consolas", 8), fg=self.c_muted, bg=self.c_card).pack(anchor="w", pady=1)

        tk.Label(right, text="TELEMETRY SUMMARY", font=("Segoe UI", 9, "bold"), fg=self.c_muted, bg=self.c_surf).pack(anchor="w", padx=14, pady=(16, 6))

        m_box = tk.Frame(right, bg=self.c_card, padx=12, pady=10, highlightbackground=self.c_border, highlightthickness=1)
        m_box.pack(fill=tk.X, padx=14, pady=3)

        self.lbl_qps = tk.Label(m_box, text="QPS: 0.0 req/s", font=("Segoe UI", 9, "bold"), fg=self.c_accent, bg=self.c_card)
        self.lbl_qps.pack(anchor="w", pady=1)

        self.lbl_hits = tk.Label(m_box, text="Total Hits: 0", font=("Segoe UI", 9), fg=self.c_text, bg=self.c_card)
        self.lbl_hits.pack(anchor="w", pady=1)

        self.lbl_bytes = tk.Label(m_box, text="Bandwidth: 0.0 KB", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_card)
        self.lbl_bytes.pack(anchor="w", pady=1)

    # =========================================================================
    # VIEW: SITES MANAGER
    # =========================================================================
    def view_sites(self):
        card = tk.Frame(self.content, bg=self.c_surf, padx=22, pady=20, highlightbackground=self.c_border, highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(card, text="MODULAR WEBSITE & APPLICATION CONTAINER MANAGER", font=("Segoe UI", 12, "bold"), fg=self.c_accent, bg=self.c_surf).pack(anchor="w")
        tk.Label(card, text="Drop any HTML/CSS/JS site, React build, or Vite bundle into the sites directory. Instant hot-switching.", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_surf).pack(anchor="w", pady=(2, 16))

        act_box = tk.Frame(card, bg=self.c_surf)
        act_box.pack(fill=tk.X, pady=(0, 16))

        tk.Button(act_box, text="📂 Open Sites Directory", font=("Segoe UI", 9, "bold"), bg=self.c_card, fg=self.c_text, bd=0, padx=14, pady=6, cursor="hand2", command=self.open_sites_folder).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(act_box, text="🔄 Refresh Sites List", font=("Segoe UI", 9), bg=self.c_card, fg=self.c_muted, bd=0, padx=14, pady=6, cursor="hand2", command=self.refresh_sites_ui).pack(side=tk.LEFT)

        tk.Label(card, text="AVAILABLE HOSTED CONTAINERS:", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_surf).pack(anchor="w", pady=(8, 6))

        self.sites_listbox = tk.Listbox(card, bg=self.c_card, fg=self.c_text, font=("Consolas", 10), bd=0, selectbackground=self.c_accent, selectforeground="#000000", height=7)
        self.sites_listbox.pack(fill=tk.X, pady=(0, 10))

        sites = self.web_server.list_available_sites()
        for s in sites:
            disp = f"  {s}  {'★ ACTIVE CONTAINER' if s == self.web_server.active_site else ''}"
            self.sites_listbox.insert(tk.END, disp)

        btn_switch = tk.Button(card, text="Activate Selected Container", font=("Segoe UI", 10, "bold"), bg=self.c_accent, fg="#000000", bd=0, padx=16, pady=8, cursor="hand2", command=self.switch_selected_site)
        btn_switch.pack(anchor="w", pady=(0, 20))

    # =========================================================================
    # VIEW: WIFI FTP CLOUD
    # =========================================================================
    def view_ftp(self):
        card = tk.Frame(self.content, bg=self.c_surf, padx=22, pady=20, highlightbackground=self.c_border, highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(card, text="WIFI FTP CLOUD SERVER CONFIGURATION", font=("Segoe UI", 12, "bold"), fg=self.c_purple, bg=self.c_surf).pack(anchor="w")
        tk.Label(card, text="Wirelessly manages server files and website templates at full router line-speed with zero internet required.", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_surf).pack(anchor="w", pady=(2, 16))

        m_row = tk.Frame(card, bg=self.c_surf)
        m_row.pack(fill=tk.X, pady=6)
        tk.Label(m_row, text="Active Storage Mount:", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_surf, width=20, anchor="w").pack(side=tk.LEFT)
        self.lbl_mount = tk.Label(m_row, text=self.ftp_server.mount_dir, font=("Consolas", 9), fg=self.c_accent, bg=self.c_card, padx=10, pady=4)
        self.lbl_mount.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(m_row, text="Browse Directory...", font=("Segoe UI", 8), bg=self.c_card, fg=self.c_text, bd=0, padx=10, pady=4, cursor="hand2", command=self.browse_ftp_mount).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(m_row, text="Mount Active Website", font=("Segoe UI", 8, "bold"), bg=self.c_card, fg=self.c_accent, bd=0, padx=10, pady=4, cursor="hand2", command=self.mount_active_website).pack(side=tk.LEFT)

        url_box = tk.Frame(card, bg="#10192b", padx=16, pady=14, highlightbackground=self.c_purple, highlightthickness=1)
        url_box.pack(fill=tk.X, pady=16)
        tk.Label(url_box, text="CONNECT FROM ANY PHONE OR PC ON YOUR LOCAL WIFI:", font=("Segoe UI", 8, "bold"), fg=self.c_purple, bg="#10192b").pack(anchor="w")
        ftp_url = self.ftp_server.get_connection_url()
        tk.Label(url_box, text=f"FTP URL:  {ftp_url}", font=("Consolas", 13, "bold"), fg="#FFFFFF", bg="#10192b").pack(anchor="w", pady=(4, 4))
        tk.Label(url_box, text="Windows File Explorer, macOS Finder, or Android File Manager: Enter the FTP URL into your address bar.", font=("Segoe UI", 8), fg=self.c_muted, bg="#10192b").pack(anchor="w")

    # =========================================================================
    # VIEW: CLOUDFLARE TUNNEL
    # =========================================================================
    def view_tunnel(self):
        card = tk.Frame(self.content, bg=self.c_surf, padx=22, pady=20, highlightbackground=self.c_border, highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(card, text="CLOUDFLARE ENCRYPTED OUTBOUND TUNNEL", font=("Segoe UI", 12, "bold"), fg=self.c_blue, bg=self.c_surf).pack(anchor="w")
        tk.Label(card, text="Establishes an outbound encrypted tunnel to Cloudflare Edge. Zero router port forwarding. Completely hides real home IP.", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_surf).pack(anchor="w", pady=(2, 14))

        q_box = tk.Frame(card, bg=self.c_card, padx=16, pady=14, highlightbackground=self.c_border, highlightthickness=1)
        q_box.pack(fill=tk.X, pady=(0, 12))

        tk.Label(q_box, text="ZERO-CONFIG QUICK TUNNEL (trycloudflare.com)", font=("Segoe UI", 9, "bold"), fg=self.c_blue, bg=self.c_card).pack(anchor="w")
        tk.Label(q_box, text="Instantly maps your local web server to an authentic global HTTPS address protected by Cloudflare DDoS mitigation.", font=("Segoe UI", 8), fg=self.c_muted, bg=self.c_card).pack(anchor="w", pady=(2, 8))

        btn_row = tk.Frame(q_box, bg=self.c_card)
        btn_row.pack(anchor="w", pady=(4, 0))
        self.btn_q_tunnel = tk.Button(
            btn_row,
            text="Disconnect Quick Tunnel" if self.tunnel_manager.is_connected else "Connect Quick Tunnel",
            font=("Segoe UI", 9, "bold"),
            bg=self.c_danger if self.tunnel_manager.is_connected else self.c_blue,
            fg="#FFFFFF", bd=0, padx=16, pady=6, cursor="hand2",
            command=self.toggle_tunnel
        )
        self.btn_q_tunnel.pack(side=tk.LEFT)

    # =========================================================================
    # VIEW: SETTINGS & THEMES
    # =========================================================================
    def view_settings(self):
        card = tk.Frame(self.content, bg=self.c_surf, padx=22, pady=20, highlightbackground=self.c_border, highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(card, text="⚙ SERVER SETTINGS & THEME PERSONALIZATION", font=("Segoe UI", 12, "bold"), fg=self.c_accent, bg=self.c_surf).pack(anchor="w")
        tk.Label(card, text="Customize the interface theme, palette, and server preferences. Settings persist across app restarts.", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_surf).pack(anchor="w", pady=(2, 16))

        tk.Label(card, text="SELECT DASHBOARD THEME:", font=("Segoe UI", 10, "bold"), fg=self.c_text, bg=self.c_surf).pack(anchor="w", pady=(0, 10))

        themes_grid = tk.Frame(card, bg=self.c_surf)
        themes_grid.pack(fill=tk.X, pady=(0, 20))

        for key, info in THEMES.items():
            is_cur = (key == self.active_theme_key)
            t_card = tk.Frame(themes_grid, bg=info["card"], padx=12, pady=10, highlightbackground=info["accent"] if is_cur else self.c_border, highlightthickness=2 if is_cur else 1)
            t_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)

            # Palette color preview circles
            c_prev = tk.Frame(t_card, bg=info["card"])
            c_prev.pack(anchor="w", pady=(0, 6))
            for color in [info["bg"], info["card"], info["accent"], info["blue"]]:
                tk.Label(c_prev, text="  ", bg=color, relief=tk.FLAT).pack(side=tk.LEFT, padx=1)

            lbl_name = tk.Label(t_card, text=info["name"].split(" (")[0], font=("Segoe UI", 9, "bold"), fg=info["text"], bg=info["card"])
            lbl_name.pack(anchor="w")

            lbl_sub = tk.Label(t_card, text="(" + info["name"].split(" (")[1], font=("Segoe UI", 7), fg=info["muted"], bg=info["card"])
            lbl_sub.pack(anchor="w", pady=(1, 6))

            btn_apply = tk.Button(
                t_card, text="Active ★" if is_cur else "Apply",
                font=("Segoe UI", 8, "bold"),
                bg=info["accent"] if is_cur else self.c_surf,
                fg="#000000" if is_cur else info["text"],
                bd=0, padx=10, pady=4, cursor="hand2",
                command=lambda k=key: self.change_theme(k)
            )
            btn_apply.pack(anchor="w")

        # Port & Network Settings Info
        net_box = tk.Frame(card, bg=self.c_card, padx=16, pady=12, highlightbackground=self.c_border, highlightthickness=1)
        net_box.pack(fill=tk.X, pady=10)
        tk.Label(net_box, text="NETWORK & DAEMON RUNTIME PREFERENCES:", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_card).pack(anchor="w")
        tk.Label(net_box, text=f"• HTTP Web Server Port: {DEFAULT_WEB_PORT}\n• WiFi FTP Server Port: {DEFAULT_FTP_PORT}\n• Settings File: {self.settings_file}\n• Active Storage Mount: {self.ftp_server.mount_dir}\n• Active Web Container: sites/{self.web_server.active_site}", font=("Consolas", 8), fg=self.c_muted, bg=self.c_card, justify=tk.LEFT).pack(anchor="w", pady=(4, 0))

    # =========================================================================
    # ACTIONS & UTILITIES
    # =========================================================================
    def open_sites_folder(self):
        if sys.platform == "win32":
            os.startfile(self.sites_dir)
        else:
            subprocess.Popen(["xdg-open", self.sites_dir])

    def open_mount_folder(self):
        target = self.ftp_server.mount_dir
        if os.path.exists(target):
            if sys.platform == "win32":
                os.startfile(target)
            else:
                subprocess.Popen(["xdg-open", target])

    def refresh_sites_ui(self):
        self.set_tab("sites")

    def switch_selected_site(self):
        sel = self.sites_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Container", "Please select a website container from the list.")
            return
        raw = self.sites_listbox.get(sel[0]).strip().split()[0]
        self.set_active_site_direct(raw)

    def set_active_site_direct(self, site_name: str):
        if self.web_server.set_active_site(site_name):
            self.log(f"[SITE MANAGER] Active website container changed to: {site_name}")
            self.refresh_sites_ui()
            site_path = os.path.join(self.sites_dir, site_name)
            self.ftp_server.set_mount_dir(site_path)
            self.log(f"[FTP] Auto-mounted WiFi FTP server to folder: {site_path}")

    def browse_ftp_mount(self):
        new_dir = filedialog.askdirectory(initialdir=self.ftp_server.mount_dir, title="Select FTP Mount Directory")
        if new_dir:
            self.ftp_server.set_mount_dir(new_dir)
            if hasattr(self, "lbl_mount") and self.lbl_mount.winfo_exists():
                self.lbl_mount.configure(text=new_dir)
            self.log(f"[FTP] Mount directory changed to: {new_dir}")

    def mount_active_website(self):
        site_path = os.path.join(self.sites_dir, self.web_server.active_site)
        self.ftp_server.set_mount_dir(site_path)
        if hasattr(self, "lbl_mount") and self.lbl_mount.winfo_exists():
            self.lbl_mount.configure(text=site_path)
        self.log(f"[FTP] Mounted to active site root: {site_path}")

    def clear_log(self):
        if hasattr(self, "log_text") and self.log_text.winfo_exists():
            self.log_text.delete("1.0", tk.END)

    def reset_telemetry(self):
        self.web_server.telemetry = type(self.web_server.telemetry)()
        self.log("[TELEMETRY] Metrics counters reset.")

    def copy_telemetry(self):
        stats = self.web_server.telemetry.get_stats()
        text = f"OmniHost Telemetry: QPS={stats['qps']}, Hits={stats['total_requests']}, Bandwidth={round(stats['total_bytes']/1024, 1)} KB, Uptime={stats['uptime_seconds']}s"
        self.copy_to_clipboard(text)

    def log(self, msg: str):
        ts = time.strftime("%H:%M:%S")
        self.log_queue.put(f"[{ts}] {msg}\n")

    def _process_log_queue(self):
        while not self.log_queue.empty():
            line = self.log_queue.get_nowait()
            if hasattr(self, "log_text") and self.log_text.winfo_exists():
                self.log_text.insert(tk.END, line)
                self.log_text.see(tk.END)
        self.after(200, self._process_log_queue)

    def _refresh_telemetry(self):
        try:
            stats = self.web_server.telemetry.get_stats()
            kb = round(stats["total_bytes"] / 1024, 1)

            # Metro Tiles Metrics
            if hasattr(self, "lbl_tile_qps") and self.lbl_tile_qps.winfo_exists():
                self.lbl_tile_qps.configure(text=f"{stats['qps']} QPS")
            if hasattr(self, "lbl_tile_hits") and self.lbl_tile_hits.winfo_exists():
                self.lbl_tile_hits.configure(text=f"Total Hits: {stats['total_requests']}")
            if hasattr(self, "lbl_tile_bytes") and self.lbl_tile_bytes.winfo_exists():
                self.lbl_tile_bytes.configure(text=f"Bandwidth: {kb} KB")

            # Radar Metrics
            if hasattr(self, "lbl_qps") and self.lbl_qps.winfo_exists():
                self.lbl_qps.configure(text=f"QPS: {stats['qps']} req/s")
            if hasattr(self, "lbl_hits") and self.lbl_hits.winfo_exists():
                self.lbl_hits.configure(text=f"Total Hits: {stats['total_requests']}")
            if hasattr(self, "lbl_bytes") and self.lbl_bytes.winfo_exists():
                self.lbl_bytes.configure(text=f"Bandwidth: {kb} KB")
        except Exception:
            pass
        self.after(2000, self._refresh_telemetry)

    def toggle_web(self):
        if self.web_server.is_running:
            self.web_server.stop()
            if hasattr(self, "btn_toggle_web") and self.btn_toggle_web.winfo_exists():
                self.btn_toggle_web.configure(text="▶ Start Web Server (:8090)", fg=self.c_success)
            if hasattr(self, "btn_tile_web_toggle") and self.btn_tile_web_toggle.winfo_exists():
                self.btn_tile_web_toggle.configure(text="▶ Start", fg="#A7F3D0")
            if hasattr(self, "lbl_metro_web_status") and self.lbl_metro_web_status.winfo_exists():
                self.lbl_metro_web_status.configure(text="○ OFFLINE", fg="#FCA5A5")
            self.log("[WEB] Server stopped.")
        else:
            self.web_server.start()
            if hasattr(self, "btn_toggle_web") and self.btn_toggle_web.winfo_exists():
                self.btn_toggle_web.configure(text="■ Stop Web Server (:8090)", fg=self.c_danger)
            if hasattr(self, "btn_tile_web_toggle") and self.btn_tile_web_toggle.winfo_exists():
                self.btn_tile_web_toggle.configure(text="■ Stop", fg="#FECACA")
            if hasattr(self, "lbl_metro_web_status") and self.lbl_metro_web_status.winfo_exists():
                self.lbl_metro_web_status.configure(text="● ONLINE", fg="#FFFFFF")
            self.log(f"[WEB] Server started on port {DEFAULT_WEB_PORT} (Serving 'beta').")

    def toggle_ftp(self):
        if self.ftp_server.is_running:
            self.ftp_server.stop()
            if hasattr(self, "btn_toggle_ftp") and self.btn_toggle_ftp.winfo_exists():
                self.btn_toggle_ftp.configure(text="▶ Start WiFi FTP Server (:2121)", fg=self.c_success)
            if hasattr(self, "btn_tile_ftp_toggle") and self.btn_tile_ftp_toggle.winfo_exists():
                self.btn_tile_ftp_toggle.configure(text="▶ Start", fg="#BFDBFE")
            if hasattr(self, "lbl_metro_ftp_status") and self.lbl_metro_ftp_status.winfo_exists():
                self.lbl_metro_ftp_status.configure(text="○ OFFLINE", fg="#FCA5A5")
            self.log("[FTP] Server stopped.")
        else:
            self.ftp_server.start()
            if hasattr(self, "btn_toggle_ftp") and self.btn_toggle_ftp.winfo_exists():
                self.btn_toggle_ftp.configure(text="■ Stop WiFi FTP Server (:2121)", fg=self.c_danger)
            if hasattr(self, "btn_tile_ftp_toggle") and self.btn_tile_ftp_toggle.winfo_exists():
                self.btn_tile_ftp_toggle.configure(text="■ Stop", fg="#FECACA")
            if hasattr(self, "lbl_metro_ftp_status") and self.lbl_metro_ftp_status.winfo_exists():
                self.lbl_metro_ftp_status.configure(text="● READY", fg="#FFFFFF")
            self.log(f"[FTP] Server started on port {DEFAULT_FTP_PORT}.")

    def toggle_tunnel(self):
        if self.tunnel_manager.is_connected:
            self.tunnel_manager.stop()
            if hasattr(self, "lbl_shield_status") and self.lbl_shield_status.winfo_exists():
                self.lbl_shield_status.configure(text="○ Tunnel Standby", fg=self.c_muted)
            if hasattr(self, "lbl_metro_tunnel_status") and self.lbl_metro_tunnel_status.winfo_exists():
                self.lbl_metro_tunnel_status.configure(text="○ STANDBY", fg="#E9D5FF")
            if hasattr(self, "card_cf_val") and self.card_cf_val.winfo_exists():
                self.card_cf_val.configure(text="https://... (Click 'Start')")
            if hasattr(self, "btn_toggle_tunnel") and self.btn_toggle_tunnel.winfo_exists():
                self.btn_toggle_tunnel.configure(text="⚡ Start Cloudflare Tunnel", bg=self.c_blue)
            if hasattr(self, "btn_tile_tunnel_toggle") and self.btn_tile_tunnel_toggle.winfo_exists():
                self.btn_tile_tunnel_toggle.configure(text="⚡ Start")
            if hasattr(self, "btn_q_tunnel") and self.btn_q_tunnel.winfo_exists():
                self.btn_q_tunnel.configure(text="Connect Quick Tunnel", bg=self.c_blue)
            self.log("[TUNNEL] Disconnected.")
        else:
            ok = self.tunnel_manager.start_quick_tunnel()
            if ok:
                if hasattr(self, "btn_toggle_tunnel") and self.btn_toggle_tunnel.winfo_exists():
                    self.btn_toggle_tunnel.configure(text="✕ Disconnect Tunnel", bg=self.c_danger)
                if hasattr(self, "btn_tile_tunnel_toggle") and self.btn_tile_tunnel_toggle.winfo_exists():
                    self.btn_tile_tunnel_toggle.configure(text="✕ Stop")
                if hasattr(self, "lbl_shield_status") and self.lbl_shield_status.winfo_exists():
                    self.lbl_shield_status.configure(text="● Connecting to Edge...", fg=self.c_warn)
                if hasattr(self, "lbl_metro_tunnel_status") and self.lbl_metro_tunnel_status.winfo_exists():
                    self.lbl_metro_tunnel_status.configure(text="● CONNECTING...", fg="#FEF08A")
                if hasattr(self, "btn_q_tunnel") and self.btn_q_tunnel.winfo_exists():
                    self.btn_q_tunnel.configure(text="Disconnect Quick Tunnel", bg=self.c_danger)
                self.log("[TUNNEL] Connecting to Cloudflare Edge...")
            else:
                self.log("[TUNNEL] Could not launch cloudflared.")

def main():
    app = OmniHostApp()
    app.mainloop()

if __name__ == "__main__":
    main()
