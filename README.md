# 🌐 OmniHost Pro — All-in-One Modular Website & High-Speed WiFi FTP Cloud Server

> **Turn any PC or Android device into a modular website host, high-speed WiFi FTP server, and encrypted public cloud node in 60 seconds.**  
> *Built with Pure Async Python, Pyftpdlib & Cloudflare Zero Trust | Zero Router Port Forwarding | 100% Origin IP Obfuscation*

[![Platform: Windows](https://img.shields.io/badge/Platform-Windows%20x64-blue.svg?style=flat-square&logo=windows)](https://github.com/Alu6hel/OmniHostServer)
[![Platform: Android](https://img.shields.io/badge/Platform-Android%20APK-green.svg?style=flat-square&logo=android)](https://github.com/Alu6hel/OmniHostServer)
[![License: Proprietary Commercial](https://img.shields.io/badge/License-Proprietary%20Commercial-purple.svg?style=flat-square)](https://github.com/Alu6hel/OmniHostServer)
[![Tests: 25 Passed](https://img.shields.io/badge/Tests-25%20Passed%20(100%25)-brightgreen.svg?style=flat-square)](https://github.com/Alu6hel/OmniHostServer)

---

## ✨ Features & Capabilities

### 1. 🚀 Modular Website Hosting Engine (`:8090`)
- **Drop-in Site Manager**: Drop any standard HTML/CSS/JS folder, React build, Vue app, or Vite export into `sites/` to host immediately.
- **1-Click Site Switcher**: Switch between live websites instantly with zero server downtime.
- **Pre-Bundled Commercial Templates**: Includes developer portfolio, SaaS enterprise landing page, and minimalist tech blog.
- **SPA Router Fallback**: Built-in routing fallback ensuring deep client routes in React/Vue/Svelte never throw 404 errors.

### 2. 📡 High-Speed RFC 959 WiFi FTP Server (`:2121`)
*Directly solves the problems causing the 2.4-star rating on Google Play's 10M+ download "WiFi FTP Server" app:*
- **"Mount Active Website"**: Snap photos or edit HTML on your phone, upload wirelessly via FTP over WiFi, and your live hosted website updates immediately!
- **Custom Mount Points**: Mount any drive, user folder, or directory with a single click.
- **Anonymous & Authenticated Modes**: Supports zero-password anonymous access or custom credentials with full read/write/delete permissions.
- **Auto LAN IP Detection**: Formats and displays instant copyable URLs (`ftp://192.168.x.x:2121`).
- **Unbreakable Stability**: Asynchronous non-blocking architecture supporting 256 concurrent connections without mid-transfer drops.

### 3. 🛡️ Cloudflare Encrypted Outbound Tunnel (100% Home IP Masking)
- **Zero Port Forwarding**: Reaches outbound to Cloudflare Anycast edge network over an encrypted TLS tunnel.
- **Masks Real Origin IP**: Public visitors only see Cloudflare IP addresses. Your ISP, home location, and router firewall are completely invisible to port scanners.
- **Quick Tunnel (`trycloudflare.com`)**: Instant free public HTTPS URL with zero configuration or account setup.
- **External Domain Wizard**: Built-in step-by-step DNS guides for **Namecheap**, **GoDaddy**, **Porkbun**, and **Squarespace**.

### 4. 🎨 Fluent Theme Switcher & Settings
- Switch between 5 themes:
  - **Fluent Dark** (Obsidian & Emerald)
  - **Cyberpunk Neon** (Cyan & Magenta)
  - **Nord Frost** (Arctic Deep Blue)
  - **Midnight Gold** (Onyx & Amber)
  - **Monochrome Slate** (Minimalist Studio)
- Preferences automatically persist in `settings.json`.

---

## 📂 Project Structure

```
WebsiteServer/
├── bin/
│   └── cloudflared.exe            # Cloudflare Tunnel outbound binary
├── sites/
│   ├── default/                   # Welcoming cloud node portal
│   ├── portfolio/                 # Modern developer & creator portfolio
│   ├── business/                  # High-conversion SaaS landing page
│   └── blog/                      # Typography-focused tech essay blog
├── src/
│   ├── web_engine/
│   │   └── website_server.py      # Multi-site HTTP engine with SPA routing & telemetry
│   ├── ftp_engine/
│   │   └── wifi_ftp_server.py     # RFC 959 non-blocking WiFi FTP server
│   ├── tunnel_engine/
│   │   └── cloudflare_tunnel.py   # Cloudflare encrypted tunnel manager
│   ├── domain_engine/
│   │   └── domain_manager.py      # External DNS wizard (Namecheap, GoDaddy, Porkbun)
│   └── ui/
│       └── omnihost_gui.py        # Fluent Dark desktop GUI with theme switcher
├── web_app/                       # Responsive mobile PWA management dashboard
│   ├── index.html
│   ├── style.css
│   ├── app.js
│   └── manifest.json
├── android/                       # Android APK project
│   ├── AndroidManifest.xml
│   └── omnihost-release.apk
├── tests/
│   └── test_omnihost_server.py    # Automated test suite (7/7 tests passing)
├── COMMERCIAL_PITCH.md            # Market strategy & competitor teardown
├── USER_MANUAL.md                 # Complete user walkthrough & setup guide
├── PRICING_TIERS.md               # Commercial pricing structure ($19 / $49 / $99)
├── QUICK_START.md                 # 60-second setup checklist
├── RELEASE_MANIFEST.json          # Build manifest & SHA-256 verification
├── CHECKSUMS.txt                  # Integrity checksums
├── OmniHostServer.exe             # Standalone Windows executable (12.3 MB)
├── omnihost.apk                   # Standalone Native Android Release APK (474 KB)
├── android_build/                 # Complete Native Android Build System
│   ├── build_apk.sh               # 1-command AAPT2, javac, d8, apksigner build script
│   ├── AndroidManifest.xml        # Full permissions, foreground service, resizeable
│   ├── src/com/omnihost/pro/      # Multi-threaded HTTP & RFC 959 FTP Java engines
│   └── assets/                    # Bundled modular sites and high-performance UI
└── run_omnihost_server.py         # Universal Python launcher (GUI & --headless)
```

---

## 🚀 Getting Started

### 1. Launch on Windows Desktop
Double-click `OmniHostServer.exe` or run:
```bash
python run_omnihost_server.py
```

### 2. Run in Headless CLI Mode (Servers, VPS, Mini-PCs)
```bash
python run_omnihost_server.py --headless
```
To enable the public Cloudflare tunnel automatically:
```bash
python run_omnihost_server.py --headless --tunnel
```

### 3. Run Automated Tests
```bash
python tests/test_omnihost_server.py
```

---

## 📜 Commercial Licensing

OmniHost Pro is distributed under the **Alumungandr Master Charter (Proprietary Commercial License)**.  
Sole Founder & Chief Architect: **David Anthony Jones ("Alu")**.  
Copyright &copy; 2026 Alumungandr. All Rights Reserved.
