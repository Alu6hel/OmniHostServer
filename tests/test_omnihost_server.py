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
import io
import zipfile

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

        cls.web = ModularWebsiteServer(sites_dir=cls.sites_dir, default_site="default", port=8290)
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

    def test_08_file_manager_page(self):
        req = urllib.request.Request("http://127.0.0.1:8290/files")
        with urllib.request.urlopen(req) as resp:
            body = resp.read().decode("utf-8")
            self.assertEqual(resp.status, 200)
            self.assertIn("WiFi File Transfer", body)

    def test_09_file_manager_list_api(self):
        req = urllib.request.Request("http://127.0.0.1:8290/api/files/list")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            folder_names = [f["name"] for f in data["folders"]]
            self.assertIn("Documents", folder_names)
            self.assertIn("Videos", folder_names)

    def test_10_file_manager_video_category(self):
        req = urllib.request.Request("http://127.0.0.1:8290/api/files/list?category=videos")
        with urllib.request.urlopen(req) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertTrue(len(data["files"]) > 0)
            for f in data["files"]:
                self.assertTrue(f["is_video"])

    def test_11_file_manager_folder_zip_streaming(self):
        import zipfile
        req = urllib.request.Request("http://127.0.0.1:8290/api/files/download-folder?path=Documents")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.headers.get("Content-Type"), "application/zip")
            zip_bytes = resp.read()
            with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
                names = zf.namelist()
                self.assertTrue(any("OmniHost_QuickStart_2026.txt" in n for n in names))

    def test_12_file_manager_media_preview_range(self):
        req = urllib.request.Request("http://127.0.0.1:8290/api/files/preview?path=Videos/Server_Demo_2026.mp4")
        req.add_header("Range", "bytes=0-10")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 206)
            self.assertIn("bytes 0-10/", resp.headers.get("Content-Range"))
            content = resp.read()
            self.assertEqual(len(content), 11)

    def test_13_speedtest_ping_download_upload(self):
        # Ping
        req = urllib.request.Request("http://127.0.0.1:8290/api/speedtest/ping")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")

        # Download 64KB
        req = urllib.request.Request("http://127.0.0.1:8290/api/speedtest/download?size=65536")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            payload = resp.read()
            self.assertEqual(len(payload), 65536)

        # Upload 32KB
        upload_data = b"X" * 32768
        req = urllib.request.Request("http://127.0.0.1:8290/api/speedtest/upload", data=upload_data, headers={"Content-Type": "application/octet-stream"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertEqual(data["received_bytes"], 32768)

    def test_14_tunnel_status_start_stop(self):
        # Initial status
        req = urllib.request.Request("http://127.0.0.1:8290/api/tunnel/status")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertIn("active", data)

        # Start tunnel
        req = urllib.request.Request("http://127.0.0.1:8290/api/tunnel/start", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertTrue(data["url"].startswith("http"))

        # Stop tunnel
        req = urllib.request.Request("http://127.0.0.1:8290/api/tunnel/stop", data=b"{}", headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")

    def test_15_set_desktop_wallpaper(self):
        # Set wallpaper with an existing image
        req = urllib.request.Request("http://127.0.0.1:8290/api/files/set-wallpaper?path=Pictures/Wallpaper_Obsidian.png")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            data = json.loads(resp.read().decode("utf-8"))
            self.assertEqual(data["status"], "ok")
            self.assertIn("applied", data)

    def test_16_webdav_rfc4918(self):
        # 1. OPTIONS
        req = urllib.request.Request("http://127.0.0.1:8290/webdav", method="OPTIONS")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertIn("1, 2", resp.headers.get("DAV", ""))
            self.assertEqual(resp.headers.get("MS-Author-Via", ""), "DAV")

        # 2. PROPFIND
        req = urllib.request.Request("http://127.0.0.1:8290/webdav", method="PROPFIND", headers={"Depth": "1"})
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 207)
            body = resp.read().decode("utf-8")
            self.assertIn("<D:multistatus", body)
            self.assertIn("<D:response>", body)

        # 3. MKCOL
        req = urllib.request.Request("http://127.0.0.1:8290/webdav/unit_test_dav", method="MKCOL")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 201)

        # 4. PUT
        content = b"OmniHost WebDAV PC Sync Verified!"
        req = urllib.request.Request("http://127.0.0.1:8290/webdav/unit_test_dav/verified.txt", data=content, method="PUT")
        with urllib.request.urlopen(req) as resp:
            self.assertIn(resp.status, (201, 204))

        # 5. GET
        req = urllib.request.Request("http://127.0.0.1:8290/webdav/unit_test_dav/verified.txt")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            self.assertEqual(resp.read(), content)

        # 6. DELETE
        req = urllib.request.Request("http://127.0.0.1:8290/webdav/unit_test_dav", method="DELETE")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 204)

    def test_17_web_app_dashboard(self):
        req = urllib.request.Request("http://127.0.0.1:8290/app")
        with urllib.request.urlopen(req) as resp:
            self.assertEqual(resp.status, 200)
            html = resp.read().decode("utf-8")
            self.assertIn("OmniHost Pro", html)
            self.assertIn("Hotspot", html)
            self.assertIn("GalaxSee Hub", html)

if __name__ == "__main__":
    unittest.main(verbosity=2)
