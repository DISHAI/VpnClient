

import json
import os
from typing import List, Dict, Any, Optional
from core.server import ServerConfig


class AppConfig:
    CONFIG_DIR = os.path.join(os.path.expanduser("~"), ".vpn_client")
    CONFIG_FILE = os.path.join(CONFIG_DIR, "config.json")
    SERVERS_FILE = os.path.join(CONFIG_DIR, "servers.json")
    SUBSCRIPTIONS_FILE = os.path.join(CONFIG_DIR, "subscriptions.json")
    
    def __init__(self):
        self.ensure_config_dir()
        self.settings = self.load_settings()
        self.servers: List[ServerConfig] = self.load_servers()
        self.subscriptions: List[Dict[str, str]] = self.load_subscriptions()
    
    def ensure_config_dir(self):
        os.makedirs(self.CONFIG_DIR, exist_ok=True)
    
    def load_settings(self) -> Dict[str, Any]:
        defaults = {
            "socks_port": 1080,
            "http_port": 8080,
            "dns_port": 5353,
            "auto_connect": False,
            "system_proxy": True,
            "theme": "dark",
            "language": "ru",
            "last_auto_update": 0,
            "dns_server": "8.8.8.8",
            "auto_update_subs": True,
            "auto_update_interval": 10800,
            "log_level": "info",
            "tun_mode": False,
            "use_singbox": False,
            "selected_server_id": "",
            "hysteria_binary": "",
            "xray_binary": "",
            "minimize_to_tray": True,
            "singbox_binary": "",
            "auto_start": False,
            "bypass_domains": "",
            "bypass_domains": "",
        }
        if os.path.exists(self.CONFIG_FILE):
            try:
                with open(self.CONFIG_FILE, 'r', encoding='utf-8') as f:
                    loaded = json.load(f)
                    defaults.update(loaded)
            except Exception:
                pass
        return defaults
    
    def save_settings(self):
        with open(self.CONFIG_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.settings, f, indent=2, ensure_ascii=False)
    
    def load_servers(self) -> List[ServerConfig]:
        if os.path.exists(self.SERVERS_FILE):
            try:
                with open(self.SERVERS_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    return [ServerConfig.from_dict(s) for s in data]
            except Exception:
                pass
        return []
    
    def save_servers(self):
        with open(self.SERVERS_FILE, 'w', encoding='utf-8') as f:
            data = [s.to_dict() for s in self.servers]
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def load_subscriptions(self) -> List[Dict[str, str]]:
        if os.path.exists(self.SUBSCRIPTIONS_FILE):
            try:
                with open(self.SUBSCRIPTIONS_FILE, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception:
                pass
        return []
    
    def save_subscriptions(self):
        with open(self.SUBSCRIPTIONS_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.subscriptions, f, indent=2, ensure_ascii=False)
    
    def add_server(self, server: ServerConfig):
        for existing in self.servers:
            if (existing.address == server.address and 
                existing.port == server.port and
                existing.server_type == server.server_type):
                idx = self.servers.index(existing)
                server.id = existing.id
                self.servers[idx] = server
                self.save_servers()
                return
        self.servers.append(server)
        self.save_servers()
    
    def remove_server(self, server_id: str):
        self.servers = [s for s in self.servers if s.id != server_id]
        self.save_servers()
    
    def get_server_by_id(self, server_id: str) -> Optional[ServerConfig]:
        for s in self.servers:
            if s.id == server_id:
                return s
        return None
    
    def add_subscription(self, name: str, url: str, traffic_info: dict = None):
        for sub in self.subscriptions:
            if sub['url'] == url:
                sub['name'] = name
                if traffic_info:
                    sub['traffic'] = traffic_info
                self.save_subscriptions()
                return
        entry = {
            'name': name,
            'url': url,
            'enabled': True,
            'traffic': traffic_info or {}
        }
        self.subscriptions.append(entry)
        self.save_subscriptions()
    
    def remove_subscription(self, url: str):
        self.subscriptions = [s for s in self.subscriptions if s['url'] != url]
        self.servers = [s for s in self.servers if s.subscription_url != url]
        self.save_subscriptions()
        self.save_servers()

    def get_bypass_domains(self) -> list:
        
        raw = self.settings.get("bypass_domains", "")
        if not raw:
            return []
        return [d.strip().lower() for d in raw.split(",") if d.strip()]