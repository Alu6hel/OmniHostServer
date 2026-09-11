# ==============================================================================
# OmniHost Pro - Main Application Entry Point
# Supports GUI Mode (Default) and Headless Cloud Mode (--headless)
# ==============================================================================

import sys
import os
import time

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def main():
    if "--headless" in sys.argv:
        from src.web_engine.website_server import ModularWebsiteServer, DEFAULT_WEB_PORT
        from src.ftp_engine.wifi_ftp_server import WiFiFTPServer, DEFAULT_FTP_PORT, get_lan_ip
        from src.tunnel_engine.cloudflare_tunnel import CloudflareTunnelManager

        print("=" * 70)
        print("  OMNIHOST PRO - MODULAR WEBSITE & WIFI FTP CLOUD SERVER")
        print("  Commercial Production Engine (Headless Mode)")
        print("=" * 70)

        lan_ip = get_lan_ip()
        base_dir = os.path.dirname(os.path.abspath(__file__))
        sites_dir = os.path.join(base_dir, "sites")
        default_mount = os.path.join(sites_dir, "default")

        def log_msg(msg):
            print(f"[{time.strftime('%H:%M:%S')}] {msg}")

        # Start Web Server
        web = ModularWebsiteServer(sites_dir=sites_dir, port=DEFAULT_WEB_PORT)
        web.start()
        log_msg(f"[*] Modular Web Server listening on http://{lan_ip}:{DEFAULT_WEB_PORT}")

        # Start WiFi FTP Server
        ftp = WiFiFTPServer(mount_dir=default_mount, port=DEFAULT_FTP_PORT, allow_anonymous=True, log_callback=log_msg)
        ftp.start()
        log_msg(f"[*] WiFi FTP Server listening on ftp://{lan_ip}:{DEFAULT_FTP_PORT} (Mounted: {default_mount})")

        # Start Cloudflare Tunnel if --tunnel is specified
        tunnel = None
        if "--tunnel" in sys.argv:
            def on_url(url):
                print(f"\n{'*' * 60}\n[!] PUBLIC HTTPS URL: {url}\n{'*' * 60}\n")

            tunnel = CloudflareTunnelManager(local_port=DEFAULT_WEB_PORT, on_url_ready=on_url, on_log=log_msg)
            tunnel.start_quick_tunnel()

        print("[*] OmniHost Pro running. Press Ctrl+C to terminate.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping servers...")
            web.stop()
            ftp.stop()
            if tunnel:
                tunnel.stop()
            print("OmniHost Pro shut down cleanly.")
    else:
        from src.ui.omnihost_gui import main as run_gui
        run_gui()

if __name__ == "__main__":
    main()
