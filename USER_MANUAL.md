# 📘 OmniHost Pro — Official User Manual & Operational Guide

Welcome to **OmniHost Pro**, the all-in-one modular website server and high-speed WiFi FTP cloud node.

---

## 🚀 1. Quick Start Guide (60 Seconds)

### On Windows Desktop:
1. Double-click `OmniHostServer.exe` (or run `python run_omnihost_server.py`).
2. The Fluent Dark dashboard will launch, automatically initializing:
   - **Modular Website Server** on `http://192.168.x.x:8090`
   - **WiFi FTP Server** on `ftp://192.168.x.x:2121`
3. Click **"Open"** on the Local Website card to view your live site.
4. Click **"Start Cloudflare Tunnel"** to instantly generate a free, encrypted public HTTPS link (`https://*.trycloudflare.com`) that safely masks your real home IP address.

---

## 📂 2. Hosting & Switching Websites

OmniHost Pro includes a drop-in modular architecture:
- All websites live inside the `sites/` folder.
- Pre-bundled templates include:
  - `default`: The official OmniHost Pro welcoming landing page.
  - `portfolio`: Dark minimalist developer/creator portfolio.
  - `business`: Enterprise SaaS landing page with CTA and feature matrix.
  - `blog`: Clean typography journal for long-form essays and updates.

### Deploying Your Own Site:
1. Open the **"Modular Sites"** tab in OmniHost Pro.
2. Click **"📂 Open Sites Directory"**.
3. Create a new folder (e.g., `myportfolio`) and drop your HTML, CSS, JavaScript, or React/Vite production build (`dist`) into it.
4. In OmniHost Pro, select `myportfolio` from the list and click **"Activate Selected Site"**. Your new site is now live!

---

## 📡 3. Wireless File Transfer & Site Editing (WiFi FTP)

OmniHost Pro solves the flaws of common mobile FTP apps by providing reliable RFC 959 async transfer:

### How to Connect from Your Smartphone:
1. Ensure your phone is on the same WiFi network as your PC.
2. Look at the **WIFI FTP SERVER URL** card (e.g., `ftp://192.168.1.150:2121`).
3. Open your phone's built-in File Manager (or apps like *AndFTP*, *Solid Explorer*, or *Documents by Readdle* on iOS).
4. Enter the FTP URL. By default, **Anonymous** access is enabled (no password needed).
5. You can now browse files, download PC documents, or upload photos wirelessly at maximum WiFi speeds!

### Live Wireless Site Updating:
In the **WiFi FTP Server** tab, click **"Mount Active Website"**. Now, whenever you upload an image or edit an HTML file from your phone over FTP, your live hosted website updates immediately!

---

## 🛡️ 4. Cloudflare Encrypted Outbound Tunnel

### How It Works:
Instead of forcing you to open ports on your home WiFi router (which leaves your network vulnerable to port scans and leaks your real home IP), OmniHost Pro reaches **outbound** to Cloudflare:
- Outbound connection to Cloudflare edge -> Encrypted TLS tunnel established.
- Public visitors browse `https://<unique-id>.trycloudflare.com`.
- Traffic is securely relayed down through the tunnel to your local machine.
- Your real home IP address, ISP, and geographic coordinates are **100% invisible**.

---

## 🌐 5. External Custom Domain Setup

To use your own registered domain (e.g., `www.yourname.com`):
1. Open the **"Cloudflare & Domains"** tab.
2. Select your registrar in the dropdown (**Namecheap**, **GoDaddy**, **Porkbun**, or **Squarespace**).
3. Follow the generated step-by-step guide to add a **CNAME** DNS record pointing to your Cloudflare Tunnel hostname.
4. Changes typically propagate within 5 to 15 minutes worldwide.

---

## ❓ Frequently Asked Questions (FAQ)

**Q: Do I need a static public IP from my Internet provider?**  
*A: No! Because Cloudflare utilizes outbound tunneling, OmniHost Pro works perfectly even behind dynamic residential IPs, CGNAT, and mobile hotspots.*

**Q: Can I run OmniHost Pro in headless mode on a server or Raspberry Pi?**  
*A: Yes! Simply run `python run_omnihost_server.py --headless` (add `--tunnel` to start the Cloudflare tunnel automatically).*

**Q: Is there any bandwidth limit on WiFi FTP transfers?**  
*A: None. WiFi FTP runs entirely across your local network at full hardware line speed (up to 1,200+ Mbps on Wi-Fi 6).*

---
*OmniHost Pro User Manual &bull; Alumungandr Master Charter &copy; 2026*
