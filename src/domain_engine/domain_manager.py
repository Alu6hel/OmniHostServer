# ==============================================================================
# OmniHost Pro - External Custom Domain Integration Wizard
# Guides users step-by-step to bind domains from Namecheap, GoDaddy, Porkbun, etc.
# ==============================================================================

import socket
from typing import Dict, List, Any

PROVIDERS = {
    "namecheap": {
        "name": "Namecheap",
        "portal_url": "https://ap.www.namecheap.com",
        "steps": [
            "1. Log in to Namecheap and click 'Domain List' on the left sidebar.",
            "2. Click 'Manage' next to your domain name.",
            "3. Navigate to the 'Advanced DNS' tab at the top.",
            "4. Under 'Host Records', click 'Add New Record'.",
            "5. Select Type: CNAME Record.",
            "6. Enter Host: '@' (for root domain) or 'www' (for www subdomain).",
            "7. Paste Target: {target}",
            "8. Set TTL: 'Automatic' and click the green checkmark to save."
        ]
    },
    "godaddy": {
        "name": "GoDaddy",
        "portal_url": "https://dcc.godaddy.com/manage/dns",
        "steps": [
            "1. Sign in to your GoDaddy Domain Portfolio.",
            "2. Select your domain and go to 'DNS' -> 'DNS Records'.",
            "3. Click 'Add New Record'.",
            "4. Choose Type: CNAME.",
            "5. Enter Name: 'www' or '@'.",
            "6. Enter Value: {target}",
            "7. Choose TTL: '1 Hour' or default.",
            "8. Click 'Save' to commit changes."
        ]
    },
    "porkbun": {
        "name": "Porkbun",
        "portal_url": "https://porkbun.com/account/domains",
        "steps": [
            "1. Log in to Porkbun and click 'Domain Management'.",
            "2. Find your domain and click 'Details' -> 'DNS Records' (Edit).",
            "3. Choose Type: CNAME.",
            "4. Enter Host: leave blank for apex domain or enter 'www'.",
            "5. Enter Answer: {target}",
            "6. Set TTL: '600' seconds.",
            "7. Click 'Submit' to publish the DNS record."
        ]
    },
    "squarespace": {
        "name": "Squarespace / Google Domains",
        "portal_url": "https://account.squarespace.com/domains",
        "steps": [
            "1. Go to your Domains Dashboard and select your domain.",
            "2. Click 'DNS Settings' -> 'Custom Records'.",
            "3. Click 'Add Record'.",
            "4. Set Record: CNAME.",
            "5. Set Host: 'www' or '@'.",
            "6. Set Data: {target}",
            "7. Click 'Save'."
        ]
    }
}

class DomainManager:
    @staticmethod
    def get_providers() -> List[str]:
        return list(PROVIDERS.keys())

    @staticmethod
    def get_guide(provider_key: str, tunnel_target: str = "your-tunnel-id.cfargotunnel.com") -> Dict[str, Any]:
        key = provider_key.lower().strip()
        info = PROVIDERS.get(key, PROVIDERS["namecheap"])
        steps = [s.format(target=tunnel_target) for s in info["steps"]]
        return {
            "key": key,
            "provider_name": info["name"],
            "portal_url": info["portal_url"],
            "target": tunnel_target,
            "steps": steps,
            "recommended_record": {
                "type": "CNAME",
                "host": "@",
                "target": tunnel_target,
                "ttl": "Auto / 300s"
            }
        }

    @staticmethod
    def test_dns(domain: str) -> Dict[str, Any]:
        """Checks if the domain resolves to an IP address."""
        clean = domain.strip().lower().replace("http://", "").replace("https://", "").split("/")[0]
        try:
            ip = socket.gethostbyname(clean)
            return {"resolved": True, "domain": clean, "ip": ip}
        except Exception as e:
            return {"resolved": False, "domain": clean, "error": str(e)}

if __name__ == "__main__":
    guide = DomainManager.get_guide("namecheap", "sub.omnihost.net")
    print("Namecheap Guide:")
    for step in guide["steps"]:
        print(" ", step)
