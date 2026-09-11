# ==============================================================================
# OmniHost Pro - Commercial Fluent Desktop GUI Dashboard
# Integrated Modular Website Host, WiFi FTP Server & Cloudflare Encrypted Tunnel
# Features: Dynamic Multi-Theme Switcher (Fluent Dark, Cyberpunk, Nord, Gold, Slate)
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

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../..")))
from src.web_engine.website_server import ModularWebsiteServer, DEFAULT_WEB_PORT
from src.ftp_engine.wifi_ftp_server import WiFiFTPServer, DEFAULT_FTP_PORT, get_lan_ip
from src.tunnel_engine.cloudflare_tunnel import CloudflareTunnelManager
from src.domain_engine.domain_manager import DomainManager

THEMES = {
    "fluent_dark": {
        "name": "Fluent Dark (Obsidian & Emerald)",
        "bg": "#080B11", "surf": "#111622", "card": "#182030",
        "accent": "#10B981", "blue": "#3B82F6", "purple": "#8B5CF6",
        "text": "#F8FAFC", "muted": "#94A3B8", "border": "#222D42"
    },
    "cyberpunk_neon": {
        "name": "Cyberpunk Neon (Cyan & Magenta)",
        "bg": "#0A0612", "surf": "#150C24", "card": "#22123B",
        "accent": "#06B6D4", "blue": "#F43F5E", "purple": "#C084FC",
        "text": "#FAF5FF", "muted": "#A855F7", "border": "#3B1861"
    },
    "nord_frost": {
        "name": "Nord Frost (Arctic Deep Blue)",
        "bg": "#0F141C", "surf": "#1A2332", "card": "#243044",
        "accent": "#38BDF8", "blue": "#60A5FA", "purple": "#818CF8",
        "text": "#F0F9FF", "muted": "#94A3B8", "border": "#334155"
    },
    "midnight_gold": {
        "name": "Midnight Gold (Onyx & Amber)",
        "bg": "#0C0A06", "surf": "#1A160C", "card": "#262012",
        "accent": "#F59E0B", "blue": "#D97706", "purple": "#FBBF24",
        "text": "#FFFBEB", "muted": "#A1A1AA", "border": "#3D341D"
    },
    "monochrome_slate": {
        "name": "Monochrome Slate (Minimalist Studio)",
        "bg": "#121214", "surf": "#1C1C1F", "card": "#27272A",
        "accent": "#E4E4E7", "blue": "#A1A1AA", "purple": "#D4D4D8",
        "text": "#FFFFFF", "muted": "#71717A", "border": "#3F3F46"
    }
}

class OmniHostApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("OmniHost Pro - Modular Website & WiFi FTP Cloud Server")
        self.geometry("1120x760")
        self.minsize(980, 640)

        # Base directories
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        self.settings_file = os.path.join(base_dir, "settings.json")
        self.active_theme_key = self._load_saved_theme()
        self._apply_palette(self.active_theme_key)

        self.configure(bg=self.c_bg)
        self.log_queue = queue.Queue()
        self.active_tab = "dashboard"

        # Core Engines
        self.sites_dir = os.path.join(base_dir, "sites")
        self.web_server = ModularWebsiteServer(sites_dir=self.sites_dir, port=DEFAULT_WEB_PORT)

        default_mount = os.path.join(self.sites_dir, "default")
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
                    th = data.get("theme", "fluent_dark")
                    if th in THEMES:
                        return th
            except Exception:
                pass
        return "fluent_dark"

    def _save_theme(self, theme_key: str):
        self.active_theme_key = theme_key
        data = {"theme": theme_key, "updated_at": time.time()}
        try:
            with open(self.settings_file, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
        except Exception:
            pass

    def _apply_palette(self, theme_key: str):
        pal = THEMES.get(theme_key, THEMES["fluent_dark"])
        self.c_bg = pal["bg"]
        self.c_surf = pal["surf"]
        self.c_card = pal["card"]
        self.c_accent = pal["accent"]
        self.c_blue = pal["blue"]
        self.c_purple = pal["purple"]
        self.c_text = pal["text"]
        self.c_muted = pal["muted"]
        self.c_border = pal["border"]
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
        self.card_cf_val.configure(text=url)
        self.lbl_shield_status.configure(text="● REAL IP MASKED (Cloudflare Anycast)", fg=self.c_blue)
        self.log(f"[SHIELD] Public HTTPS Route Active: {url}")

    def setup_ui(self):
        for w in self.winfo_children():
            w.destroy()

        # Top Navigation & Branding
        top_bar = tk.Frame(self, bg=self.c_surf, height=64)
        top_bar.pack(side=tk.TOP, fill=tk.X)
        top_bar.pack_propagate(False)

        brand = tk.Frame(top_bar, bg=self.c_surf)
        brand.pack(side=tk.LEFT, padx=20, pady=10)

        tk.Label(brand, text="🌐 OMNIHOST PRO", font=("Segoe UI", 13, "bold"), fg=self.c_accent, bg=self.c_surf).pack(anchor="w")
        tk.Label(brand, text="All-in-One Modular Website & WiFi FTP Cloud Server", font=("Segoe UI", 8), fg=self.c_muted, bg=self.c_surf).pack(anchor="w")

        # Tabs in Header
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
                bg=bg, fg=fg, bd=0, padx=12, pady=6, cursor="hand2",
                command=lambda t=tid: self.set_tab(t)
            ).pack(side=tk.LEFT, padx=3)

        # Shield Status
        self.lbl_shield_status = tk.Label(top_bar, text="○ Tunnel Standby", font=("Consolas", 9, "bold"), fg=self.c_muted, bg=self.c_card, padx=12, pady=6)
        self.lbl_shield_status.pack(side=tk.RIGHT, padx=20, pady=16)

        # Hero URL Cards
        hero_bar = tk.Frame(self, bg=self.c_bg)
        hero_bar.pack(fill=tk.X, padx=20, pady=(14, 6))

        lan_ip = get_lan_ip()

        # 1. Local Web URL
        c1 = tk.Frame(hero_bar, bg=self.c_surf, padx=14, pady=10, highlightbackground=self.c_border, highlightthickness=1)
        c1.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        tk.Label(c1, text="LOCAL WEBSITE URL", font=("Segoe UI", 8, "bold"), fg=self.c_muted, bg=self.c_surf).pack(anchor="w")
        self.card_web_val = tk.Label(c1, text=f"http://{lan_ip}:{DEFAULT_WEB_PORT}", font=("Consolas", 10, "bold"), fg=self.c_accent, bg=self.c_surf)
        self.card_web_val.pack(anchor="w", pady=(2, 4))
        btn_box1 = tk.Frame(c1, bg=self.c_surf)
        btn_box1.pack(anchor="w")
        tk.Button(btn_box1, text="Open", font=("Segoe UI", 8), bg=self.c_card, fg=self.c_text, bd=0, padx=8, pady=2, cursor="hand2", command=lambda: webbrowser.open(f"http://localhost:{DEFAULT_WEB_PORT}")).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(btn_box1, text="Copy", font=("Segoe UI", 8), bg=self.c_card, fg=self.c_muted, bd=0, padx=8, pady=2, cursor="hand2", command=lambda: self.copy_to_clipboard(f"http://{lan_ip}:{DEFAULT_WEB_PORT}")).pack(side=tk.LEFT)

        # 2. WiFi FTP URL
        c2 = tk.Frame(hero_bar, bg=self.c_surf, padx=14, pady=10, highlightbackground=self.c_border, highlightthickness=1)
        c2.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        tk.Label(c2, text="WIFI FTP SERVER URL", font=("Segoe UI", 8, "bold"), fg=self.c_muted, bg=self.c_surf).pack(anchor="w")
        self.card_ftp_val = tk.Label(c2, text=f"ftp://{lan_ip}:{DEFAULT_FTP_PORT}", font=("Consolas", 10, "bold"), fg=self.c_purple, bg=self.c_surf)
        self.card_ftp_val.pack(anchor="w", pady=(2, 4))
        btn_box2 = tk.Frame(c2, bg=self.c_surf)
        btn_box2.pack(anchor="w")
        tk.Button(btn_box2, text="Copy FTP URL", font=("Segoe UI", 8), bg=self.c_card, fg=self.c_text, bd=0, padx=8, pady=2, cursor="hand2", command=lambda: self.copy_to_clipboard(f"ftp://{lan_ip}:{DEFAULT_FTP_PORT}")).pack(side=tk.LEFT)

        # 3. Cloudflare Tunnel URL
        c3 = tk.Frame(hero_bar, bg=self.c_surf, padx=14, pady=10, highlightbackground=self.c_border, highlightthickness=1)
        c3.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=4)
        tk.Label(c3, text="CLOUDFLARE PUBLIC HTTPS (IP MASKED)", font=("Segoe UI", 8, "bold"), fg=self.c_muted, bg=self.c_surf).pack(anchor="w")
        self.card_cf_val = tk.Label(c3, text="https://... (Click 'Start Tunnel')", font=("Consolas", 10, "bold"), fg=self.c_blue, bg=self.c_surf)
        self.card_cf_val.pack(anchor="w", pady=(2, 4))
        btn_box3 = tk.Frame(c3, bg=self.c_surf)
        btn_box3.pack(anchor="w")
        tk.Button(btn_box3, text="Copy HTTPS", font=("Segoe UI", 8), bg=self.c_card, fg=self.c_text, bd=0, padx=8, pady=2, cursor="hand2", command=lambda: self.copy_to_clipboard(self.card_cf_val.cget("text"))).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(btn_box3, text="Open Link", font=("Segoe UI", 8), bg=self.c_card, fg=self.c_muted, bd=0, padx=8, pady=2, cursor="hand2", command=lambda: self.open_cf_link()).pack(side=tk.LEFT)

        # Main Dynamic Content Frame
        self.content = tk.Frame(self, bg=self.c_bg)
        self.content.pack(fill=tk.BOTH, expand=True, padx=20, pady=(6, 16))

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
    # VIEW: SETTINGS & THEMES
    # =========================================================================
    def view_settings(self):
        card = tk.Frame(self.content, bg=self.c_surf, padx=24, pady=24, highlightbackground=self.c_border, highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(card, text="⚙ SERVER SETTINGS & THEME CUSTOMIZATION", font=("Segoe UI", 12, "bold"), fg=self.c_accent, bg=self.c_surf).pack(anchor="w")
        tk.Label(card, text="Customize the interface theme, palette, and server preferences. Settings persist across app restarts.", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_surf).pack(anchor="w", pady=(2, 18))

        tk.Label(card, text="CHOOSE APPLICATION THEME:", font=("Segoe UI", 10, "bold"), fg=self.c_text, bg=self.c_surf).pack(anchor="w", pady=(0, 10))

        themes_grid = tk.Frame(card, bg=self.c_surf)
        themes_grid.pack(fill=tk.X, pady=(0, 20))

        for key, info in THEMES.items():
            is_cur = (key == self.active_theme_key)
            t_card = tk.Frame(themes_grid, bg=info["card"], padx=14, pady=12, highlightbackground=info["accent"] if is_cur else self.c_border, highlightthickness=2 if is_cur else 1)
            t_card.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=5)

            # Palette color preview circles
            c_prev = tk.Frame(t_card, bg=info["card"])
            c_prev.pack(anchor="w", pady=(0, 8))
            for color in [info["bg"], info["card"], info["accent"], info["blue"]]:
                tk.Label(c_prev, text="  ", bg=color, relief=tk.FLAT).pack(side=tk.LEFT, padx=1)

            lbl_name = tk.Label(t_card, text=info["name"].split(" (")[0], font=("Segoe UI", 9, "bold"), fg=info["text"], bg=info["card"])
            lbl_name.pack(anchor="w")

            lbl_sub = tk.Label(t_card, text="(" + info["name"].split(" (")[1], font=("Segoe UI", 7), fg=info["muted"], bg=info["card"])
            lbl_sub.pack(anchor="w", pady=(1, 8))

            btn_apply = tk.Button(
                t_card, text="Active Theme ★" if is_cur else "Apply Theme",
                font=("Segoe UI", 8, "bold"),
                bg=info["accent"] if is_cur else self.c_surf,
                fg="#000000" if is_cur else info["text"],
                bd=0, padx=10, pady=4, cursor="hand2",
                command=lambda k=key: self.change_theme(k)
            )
            btn_apply.pack(anchor="w")

        # Port & Network Settings Info
        net_box = tk.Frame(card, bg=self.c_card, padx=16, pady=14, highlightbackground=self.c_border, highlightthickness=1)
        net_box.pack(fill=tk.X, pady=10)
        tk.Label(net_box, text="NETWORK & DAEMON PREFERENCES:", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_card).pack(anchor="w")
        tk.Label(net_box, text=f"• HTTP Web Server Port: {DEFAULT_WEB_PORT}\n• WiFi FTP Server Port: {DEFAULT_FTP_PORT}\n• Settings Configuration File: {self.settings_file}\n• Active Storage Mount: {self.ftp_server.mount_dir}", font=("Consolas", 8), fg=self.c_muted, bg=self.c_card, justify=tk.LEFT).pack(anchor="w", pady=(4, 0))

    # =========================================================================
    # VIEW: DASHBOARD
    # =========================================================================
    def view_dashboard(self):
        split = tk.Frame(self.content, bg=self.c_bg)
        split.pack(fill=tk.BOTH, expand=True)

        left = tk.Frame(split, bg=self.c_surf, highlightbackground=self.c_border, highlightthickness=1)
        left.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=(0, 10))

        log_hdr = tk.Frame(left, bg=self.c_surf)
        log_hdr.pack(fill=tk.X, padx=14, pady=10)
        tk.Label(log_hdr, text="REAL-TIME TRAFFIC & SYSTEM LOG", font=("Segoe UI", 10, "bold"), fg=self.c_text, bg=self.c_surf).pack(side=tk.LEFT)

        self.log_text = tk.Text(left, bg="#080C13", fg="#CBD5E1", font=("Consolas", 9), bd=0, padx=12, pady=10)
        self.log_text.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 12))

        right = tk.Frame(split, bg=self.c_surf, width=280, highlightbackground=self.c_border, highlightthickness=1)
        right.pack(side=tk.RIGHT, fill=tk.Y)
        right.pack_propagate(False)

        tk.Label(right, text="SERVER CONTROLS", font=("Segoe UI", 10, "bold"), fg=self.c_text, bg=self.c_surf).pack(anchor="w", padx=16, pady=(14, 8))

        self.btn_toggle_web = tk.Button(
            right, text="Stop Web Server", font=("Segoe UI", 9, "bold"),
            bg=self.c_card, fg=self.c_danger, bd=0, padx=12, pady=8, cursor="hand2",
            command=self.toggle_web
        )
        self.btn_toggle_web.pack(fill=tk.X, padx=16, pady=4)

        self.btn_toggle_ftp = tk.Button(
            right, text="Stop WiFi FTP Server", font=("Segoe UI", 9, "bold"),
            bg=self.c_card, fg=self.c_danger, bd=0, padx=12, pady=8, cursor="hand2",
            command=self.toggle_ftp
        )
        self.btn_toggle_ftp.pack(fill=tk.X, padx=16, pady=4)

        self.btn_toggle_tunnel = tk.Button(
            right, text="Start Cloudflare Tunnel", font=("Segoe UI", 9, "bold"),
            bg=self.c_blue, fg="#FFFFFF", bd=0, padx=12, pady=8, cursor="hand2",
            command=self.toggle_tunnel
        )
        self.btn_toggle_tunnel.pack(fill=tk.X, padx=16, pady=4)

        tk.Label(right, text="PERFORMANCE METRICS", font=("Segoe UI", 9, "bold"), fg=self.c_muted, bg=self.c_surf).pack(anchor="w", padx=16, pady=(20, 6))

        m_box = tk.Frame(right, bg=self.c_card, padx=12, pady=10)
        m_box.pack(fill=tk.X, padx=16, pady=4)

        self.lbl_qps = tk.Label(m_box, text="QPS: 0.0 req/s", font=("Segoe UI", 9), fg=self.c_accent, bg=self.c_card)
        self.lbl_qps.pack(anchor="w", pady=1)

        self.lbl_hits = tk.Label(m_box, text="Total Hits: 0", font=("Segoe UI", 9), fg=self.c_text, bg=self.c_card)
        self.lbl_hits.pack(anchor="w", pady=1)

        self.lbl_bytes = tk.Label(m_box, text="Bandwidth: 0 KB", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_card)
        self.lbl_bytes.pack(anchor="w", pady=1)

    # =========================================================================
    # VIEW: SITES, FTP, TUNNEL
    # =========================================================================
    def view_sites(self):
        card = tk.Frame(self.content, bg=self.c_surf, padx=20, pady=20, highlightbackground=self.c_border, highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(card, text="MODULAR WEBSITE MANAGER", font=("Segoe UI", 12, "bold"), fg=self.c_accent, bg=self.c_surf).pack(anchor="w")
        tk.Label(card, text="Drop any HTML/CSS/JS site, React build, or Vite export into the sites folder. Switch live sites instantly.", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_surf).pack(anchor="w", pady=(2, 16))

        act_box = tk.Frame(card, bg=self.c_surf)
        act_box.pack(fill=tk.X, pady=(0, 16))

        tk.Button(act_box, text="📂 Open Sites Directory", font=("Segoe UI", 9, "bold"), bg=self.c_card, fg=self.c_text, bd=0, padx=14, pady=6, cursor="hand2", command=self.open_sites_folder).pack(side=tk.LEFT, padx=(0, 8))
        tk.Button(act_box, text="🔄 Refresh Sites List", font=("Segoe UI", 9), bg=self.c_card, fg=self.c_muted, bd=0, padx=14, pady=6, cursor="hand2", command=self.refresh_sites_ui).pack(side=tk.LEFT)

        tk.Label(card, text="AVAILABLE HOSTED SITES:", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_surf).pack(anchor="w", pady=(8, 6))

        self.sites_listbox = tk.Listbox(card, bg=self.c_card, fg=self.c_text, font=("Consolas", 10), bd=0, selectbackground=self.c_accent, selectforeground="#000000", height=6)
        self.sites_listbox.pack(fill=tk.X, pady=(0, 10))

        sites = self.web_server.list_available_sites()
        for s in sites:
            disp = f"  {s}  {'★ ACTIVE' if s == self.web_server.active_site else ''}"
            self.sites_listbox.insert(tk.END, disp)

        btn_switch = tk.Button(card, text="Activate Selected Site", font=("Segoe UI", 10, "bold"), bg=self.c_accent, fg="#000000", bd=0, padx=16, pady=8, cursor="hand2", command=self.switch_selected_site)
        btn_switch.pack(anchor="w", pady=(0, 20))

    def view_ftp(self):
        card = tk.Frame(self.content, bg=self.c_surf, padx=20, pady=20, highlightbackground=self.c_border, highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(card, text="WIFI FTP SERVER CONFIGURATION", font=("Segoe UI", 12, "bold"), fg=self.c_purple, bg=self.c_surf).pack(anchor="w")
        tk.Label(card, text="Directly resolves all flaws of the 2.4-star Google Play app. Wireless site management and local file sync.", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_surf).pack(anchor="w", pady=(2, 16))

        m_row = tk.Frame(card, bg=self.c_surf)
        m_row.pack(fill=tk.X, pady=6)
        tk.Label(m_row, text="Active Mount Point:", font=("Segoe UI", 9, "bold"), fg=self.c_text, bg=self.c_surf, width=18, anchor="w").pack(side=tk.LEFT)
        self.lbl_mount = tk.Label(m_row, text=self.ftp_server.mount_dir, font=("Consolas", 9), fg=self.c_accent, bg=self.c_card, padx=10, pady=4)
        self.lbl_mount.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 8))
        tk.Button(m_row, text="Browse Directory...", font=("Segoe UI", 8), bg=self.c_card, fg=self.c_text, bd=0, padx=10, pady=4, cursor="hand2", command=self.browse_ftp_mount).pack(side=tk.LEFT, padx=(0, 4))
        tk.Button(m_row, text="Mount Active Website", font=("Segoe UI", 8, "bold"), bg=self.c_card, fg=self.c_accent, bd=0, padx=10, pady=4, cursor="hand2", command=self.mount_active_website).pack(side=tk.LEFT)

        url_box = tk.Frame(card, bg="#161224", padx=16, pady=12, highlightbackground=self.c_purple, highlightthickness=1)
        url_box.pack(fill=tk.X, pady=14)
        tk.Label(url_box, text="CONNECT FROM ANY PHONE OR PC ON YOUR WIFI:", font=("Segoe UI", 8, "bold"), fg=self.c_purple, bg="#161224").pack(anchor="w")
        ftp_url = self.ftp_server.get_connection_url()
        tk.Label(url_box, text=f"URL:  {ftp_url}", font=("Consolas", 12, "bold"), fg="#FFFFFF", bg="#161224").pack(anchor="w", pady=(4, 4))

    def view_tunnel(self):
        card = tk.Frame(self.content, bg=self.c_surf, padx=20, pady=20, highlightbackground=self.c_border, highlightthickness=1)
        card.pack(fill=tk.BOTH, expand=True)

        tk.Label(card, text="CLOUDFLARE ENCRYPTED OUTBOUND TUNNEL & CUSTOM DOMAIN WIZARD", font=("Segoe UI", 12, "bold"), fg=self.c_blue, bg=self.c_surf).pack(anchor="w")
        tk.Label(card, text="Establishes an outbound encrypted tunnel to Cloudflare Edge. Zero router port forwarding. Completely hides real home IP.", font=("Segoe UI", 9), fg=self.c_muted, bg=self.c_surf).pack(anchor="w", pady=(2, 14))

        q_box = tk.Frame(card, bg=self.c_card, padx=14, pady=12, highlightbackground=self.c_border, highlightthickness=1)
        q_box.pack(fill=tk.X, pady=(0, 12))

        tk.Label(q_box, text="MODE 1: ZERO-CONFIG QUICK TUNNEL (trycloudflare.com)", font=("Segoe UI", 9, "bold"), fg=self.c_blue, bg=self.c_card).pack(anchor="w")
        btn_row = tk.Frame(q_box, bg=self.c_card)
        btn_row.pack(anchor="w", pady=(6, 0))
        self.btn_q_tunnel = tk.Button(
            btn_row,
            text="Disconnect Quick Tunnel" if self.tunnel_manager.is_connected else "Connect Quick Tunnel",
            font=("Segoe UI", 9, "bold"),
            bg=self.c_danger if self.tunnel_manager.is_connected else self.c_blue,
            fg="#FFFFFF", bd=0, padx=14, pady=6, cursor="hand2",
            command=self.toggle_tunnel
        )
        self.btn_q_tunnel.pack(side=tk.LEFT)

    def open_sites_folder(self):
        if sys.platform == "win32":
            os.startfile(self.sites_dir)
        else:
            subprocess.Popen(["xdg-open", self.sites_dir])

    def refresh_sites_ui(self):
        self.set_tab("sites")

    def switch_selected_site(self):
        sel = self.sites_listbox.curselection()
        if not sel:
            messagebox.showinfo("Select Site", "Please select a site from the list first.")
            return
        raw = self.sites_listbox.get(sel[0]).strip().split()[0]
        self.set_active_site_direct(raw)

    def set_active_site_direct(self, site_name: str):
        if self.web_server.set_active_site(site_name):
            self.log(f"[SITE MANAGER] Active website changed to: {site_name}")
            self.refresh_sites_ui()
            site_path = os.path.join(self.sites_dir, site_name)
            self.ftp_server.set_mount_dir(site_path)
            self.log(f"[FTP] Auto-mounted WiFi FTP server to active site folder: {site_path}")

    def browse_ftp_mount(self):
        new_dir = filedialog.askdirectory(initialdir=self.ftp_server.mount_dir, title="Select FTP Mount Directory")
        if new_dir:
            self.ftp_server.set_mount_dir(new_dir)
            self.lbl_mount.configure(text=new_dir)
            self.log(f"[FTP] Mount directory changed to: {new_dir}")

    def mount_active_website(self):
        site_path = os.path.join(self.sites_dir, self.web_server.active_site)
        self.ftp_server.set_mount_dir(site_path)
        self.lbl_mount.configure(text=site_path)
        self.log(f"[FTP] Mounted to active site root: {site_path}")

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
            if hasattr(self, "lbl_qps") and self.lbl_qps.winfo_exists():
                self.lbl_qps.configure(text=f"QPS: {stats['qps']} req/s")
                self.lbl_hits.configure(text=f"Total Hits: {stats['total_requests']}")
                kb = round(stats["total_bytes"] / 1024, 1)
                self.lbl_bytes.configure(text=f"Bandwidth: {kb} KB")
        except Exception:
            pass
        self.after(2000, self._refresh_telemetry)

    def toggle_web(self):
        if self.web_server.is_running:
            self.web_server.stop()
            self.btn_toggle_web.configure(text="Start Web Server", fg=self.c_success)
            self.log("[WEB] Server stopped.")
        else:
            self.web_server.start()
            self.btn_toggle_web.configure(text="Stop Web Server", fg=self.c_danger)
            self.log(f"[WEB] Server started on port {DEFAULT_WEB_PORT}.")

    def toggle_ftp(self):
        if self.ftp_server.is_running:
            self.ftp_server.stop()
            self.btn_toggle_ftp.configure(text="Start WiFi FTP Server", fg=self.c_success)
            self.log("[FTP] Server stopped.")
        else:
            self.ftp_server.start()
            self.btn_toggle_ftp.configure(text="Stop WiFi FTP Server", fg=self.c_danger)
            self.log(f"[FTP] Server started on port {DEFAULT_FTP_PORT}.")

    def toggle_tunnel(self):
        if self.tunnel_manager.is_connected:
            self.tunnel_manager.stop()
            self.lbl_shield_status.configure(text="○ Tunnel Standby", fg=self.c_muted)
            self.card_cf_val.configure(text="https://... (Click 'Start Tunnel')")
            if hasattr(self, "btn_toggle_tunnel"):
                self.btn_toggle_tunnel.configure(text="Start Cloudflare Tunnel", bg=self.c_blue)
            self.log("[TUNNEL] Disconnected.")
        else:
            ok = self.tunnel_manager.start_quick_tunnel()
            if ok:
                if hasattr(self, "btn_toggle_tunnel"):
                    self.btn_toggle_tunnel.configure(text="Disconnect Tunnel", bg=self.c_danger)
                self.lbl_shield_status.configure(text="● Connecting to Cloudflare...", fg=self.c_warn)
                self.log("[TUNNEL] Connecting to Cloudflare Edge...")
            else:
                self.log("[TUNNEL] Could not launch cloudflared.")

def main():
    app = OmniHostApp()
    app.mainloop()

if __name__ == "__main__":
    main()
