# ==============================================================================
# OmniHost Pro - Beta Site Launcher
# Starts the web server with the beta site active + Cloudflare tunnel
# ==============================================================================

import sys
import os
import time

sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

def main():
    from src.web_engine.website_server import ModularWebsiteServer, DEFAULT_WEB_PORT
    from src.tunnel_engine.cloudflare_tunnel import CloudflareTunnelManager

    print("=" * 70)
    print("  ALUMUNGANDR BETA TESTING SITE")
    print("  Powered by OmniHost Pro")
    print("=" * 70)

    base_dir = os.path.dirname(os.path.abspath(__file__))
    sites_dir = os.path.join(base_dir, "sites")

    # Start Web Server with beta site active
    web = ModularWebsiteServer(sites_dir=sites_dir, default_site="beta", port=DEFAULT_WEB_PORT)
    web.start()
    print(f"[*] Beta site live on http://127.0.0.1:{DEFAULT_WEB_PORT}")

    # Start Cloudflare quick tunnel for public access
    public_url = None
    def on_url(url):
        nonlocal public_url
        public_url = url
        print(f"\n{'*' * 60}")
        print(f"  YOUR BETA SITE IS LIVE!")
        print(f"  PUBLIC URL: {url}")
        print(f"{'*' * 60}\n")
        try:
            storage_dir = os.path.join(base_dir, "storage")
            os.makedirs(storage_dir, exist_ok=True)
            with open(os.path.join(storage_dir, "public_url.txt"), "w", encoding="utf-8") as f:
                f.write(url.strip())
        except Exception:
            pass

    def on_log(msg):
        print(f"[TUNNEL] {msg}")

    tunnel = CloudflareTunnelManager(local_port=DEFAULT_WEB_PORT, on_url_ready=on_url, on_log=on_log)
    tunnel.start_quick_tunnel()

    print("[*] Waiting for Cloudflare tunnel to connect...")
    print("[*] Press Ctrl+C to shut down.\n")

    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\nShutting down...")
        web.stop()
        tunnel.stop()
        print("Beta site stopped cleanly.")

if __name__ == "__main__":
    main()
