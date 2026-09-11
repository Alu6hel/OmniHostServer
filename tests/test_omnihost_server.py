# ==============================================================================
# Automated Test Suite for OmniHost Pro
# Verifies Modular Web Engine, Multi-Site Switching, SPA Fallback, WiFi FTP Server,
# Cloudflare Tunnel Manager, and External Domain Manager
# ==============================================================================

import os
import sys
import time
import json
import ftplib
import unittest
import urllib.request
import urllib.parse

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
from src.web_engine.website_server import ModularWebsiteServer
from src.ftp_engine.wifi_ftp_server import WiFiFTPServer
from src.tunnel_engine.cloudflare_tunnel import CloudflareTunnelManager
from src.domain_engine.domain_manager import DomainManager

class TestOmniHostServer(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        base = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
        cls.sites_dir = os.path.join(base, "sites")

        cls.web = ModularWebsiteServer(sites_dir=cls.sites_dir, port=8290)
        cls.web.start()

        mount = os.path.join(cls.sites_dir, "default")
        cls.ftp = WiFiFTPServer(mount_dir=mount, port=2221, allow_anonymous=True)
        cls.ftp.start()

        time.sleep(0.6)

    @classmethod
    def tearDownClass(cls):
        cls.web.stop()
        cls.ftp.stop()

    def test_01_web_status_api(self):
        req = urllib.request.Request("http://127.0.0.1:8290/api/status")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(resp.status, 200)
            self.assertIn("active_site", data)
            self.assertIn("available_sites", data)
            self.assertEqual(data["active_port"], 8290)

    def test_02_static_site_serving(self):
        req = urllib.request.Request("http://127.0.0.1:8290/")
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            self.assertEqual(resp.status, 200)
            self.assertIn("OmniHost Pro", content)

    def test_03_multi_site_switching(self):
        # Switch to portfolio
        payload = json.dumps({"site_name": "portfolio"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8290/api/switch-site", data=payload, headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["active_site"], "portfolio")

        # Verify portfolio content is now served at root
        req = urllib.request.Request("http://127.0.0.1:8290/")
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            self.assertIn("Alex River", content)

        # Switch back to default
        payload = json.dumps({"site_name": "default"}).encode("utf-8")
        req = urllib.request.Request("http://127.0.0.1:8290/api/switch-site", data=payload, headers={"Content-Type": "application/json"})
        urllib.request.urlopen(req)

    def test_04_spa_router_fallback(self):
        # When hitting a deep route without extension like /dashboard/settings
        req = urllib.request.Request("http://127.0.0.1:8290/dashboard/settings")
        with urllib.request.urlopen(req) as resp:
            content = resp.read().decode("utf-8")
            self.assertEqual(resp.status, 200)
            self.assertIn("OmniHost Pro", content)

    def test_05_wifi_ftp_operations(self):
        client = ftplib.FTP()
        client.connect("127.0.0.1", 2221)
        client.login("anonymous", "")
        listing = client.nlst()
        self.assertIsInstance(listing, list)

        # Upload a test file via FTP
        import io
        test_data = io.BytesIO(b"Hello WiFi FTP from OmniHost Pro!")
        client.storbinary("STOR omni_test.txt", test_data)

        # Verify file is in listing
        listing_after = client.nlst()
        self.assertIn("omni_test.txt", listing_after)

        # Clean up
        client.delete("omni_test.txt")
        client.quit()

    def test_06_cloudflare_tunnel_manager(self):
        tunnel = CloudflareTunnelManager(local_port=8290)
        self.assertTrue(os.path.exists(tunnel.binary_path))

    def test_07_domain_manager_guides(self):
        guide = DomainManager.get_guide("namecheap", "test-tunnel.cfargotunnel.com")
        self.assertEqual(guide["provider_name"], "Namecheap")
        self.assertEqual(len(guide["steps"]), 8)
        self.assertIn("test-tunnel.cfargotunnel.com", guide["steps"][6])

        godaddy_guide = DomainManager.get_guide("godaddy", "test-tunnel.cfargotunnel.com")
        self.assertEqual(godaddy_guide["provider_name"], "GoDaddy")

if __name__ == "__main__":
    unittest.main(verbosity=2)
