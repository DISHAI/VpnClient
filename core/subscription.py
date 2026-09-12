

import requests
import threading
import base64
from typing import List, Callable, Optional
from core.server import ServerConfig
from utils.parser import URIParser
from utils.logger import get_logger


class SubscriptionInfo:
    def __init__(self):
        self.upload: int = 0
        self.download: int = 0
        self.total: int = 0
        self.expire: str = ""
        self.web_page: str = ""
        self.update_interval: int = 0
        self.title: str = ""

    @property
    def used(self) -> int:
        return self.upload + self.download

    @property
    def remaining(self) -> int:
        if self.total <= 0:
            return -1
        return max(0, self.total - self.used)

    def has_data(self) -> bool:
        return (
            self.upload > 0 or
            self.download > 0 or
            self.total > 0 or
            bool(self.expire) or
            bool(self.web_page) or
            bool(self.title)
        )

    @staticmethod
    def format_bytes(b: int) -> str:
        if b < 0:
            return "∞"
        if b == 0:
            return "0 B"
        units = ["B", "KB", "MB", "GB", "TB"]
        i = 0
        val = float(b)
        while val >= 1024 and i < len(units) - 1:
            val /= 1024
            i += 1
        return f"{val:.1f} {units[i]}"

    def used_str(self) -> str:
        return self.format_bytes(self.used)

    def total_str(self) -> str:
        if self.total <= 0:
            return "∞"
        return self.format_bytes(self.total)

    def remaining_str(self) -> str:
        return self.format_bytes(self.remaining)

    def percent_used(self) -> float:
        if self.total <= 0:
            return 0
        return min(100, (self.used / self.total) * 100)

    def to_dict(self) -> dict:
        return {
            "upload": self.upload,
            "download": self.download,
            "total": self.total,
            "expire": self.expire,
            "web_page": self.web_page,
            "update_interval": self.update_interval,
            "title": self.title,
        }

    @classmethod
    def from_dict(cls, data: dict) -> "SubscriptionInfo":
        info = cls()
        info.upload = data.get("upload", 0)
        info.download = data.get("download", 0)
        info.total = data.get("total", 0)
        info.expire = data.get("expire", "")
        info.web_page = data.get("web_page", "")
        info.update_interval = data.get("update_interval", 0)
        info.title = data.get("title", "")
        return info


class SubscriptionManager:
    def __init__(self):
        self.logger = get_logger()

    def fetch_subscription(self, url: str, timeout: int = 15):
        self.logger.info(f"Загрузка подписки: {url}")

        try:
            headers = {
                "User-Agent": "VPNClient/1.0",
                "Accept": "*/*",
            }

            response = requests.get(url, headers=headers, timeout=timeout)
            response.raise_for_status()

            self.logger.info("Заголовки ответа:")
            for key, val in response.headers.items():
                self.logger.info(f"  {key}: {val}")

            sub_info = self._parse_subscription_headers(response.headers)

            content = response.text
            servers = URIParser.parse_subscription_content(content)

            for server in servers:
                server.subscription_url = url
                if sub_info:
                    server.sub_traffic_used = sub_info.used
                    server.sub_traffic_total = sub_info.total
                    server.sub_expiry = sub_info.expire

            self.logger.info(f"Загружено {len(servers)} серверов")
            return servers, sub_info

        except requests.exceptions.Timeout:
            self.logger.error(f"Таймаут: {url}")
            return [], None
        except requests.exceptions.RequestException as e:
            self.logger.error(f"Ошибка загрузки: {e}")
            return [], None
        except Exception as e:
            self.logger.error(f"Ошибка парсинга подписки: {e}")
            return [], None

    def _parse_subscription_headers(self, headers) -> Optional[SubscriptionInfo]:
        info = SubscriptionInfo()
        found = False

        for header_name in ["subscription-userinfo", "x-subscription-userinfo", "userinfo"]:
            userinfo = headers.get(header_name, "")
            if userinfo:
                found = True
                for part in userinfo.split(";"):
                    part = part.strip()
                    if "=" in part:
                        key, val = part.split("=", 1)
                        key = key.strip().lower()
                        val = val.strip()
                        try:
                            if key == "upload":
                                info.upload = int(val)
                            elif key == "download":
                                info.download = int(val)
                            elif key == "total":
                                info.total = int(val)
                            elif key == "expire":
                                info.expire = self._parse_expire(val)
                        except Exception:
                            pass
                break

        info.web_page = headers.get("profile-web-page-url", "")

        try:
            info.update_interval = int(headers.get("profile-update-interval", "0"))
        except Exception:
            info.update_interval = 0

        profile_title = headers.get("profile-title", "")
        if profile_title:
            try:
                if profile_title.startswith("base64:"):
                    encoded = profile_title.split("base64:", 1)[1]
                    info.title = base64.b64decode(encoded).decode("utf-8", errors="ignore")
                else:
                    info.title = profile_title
            except Exception:
                info.title = profile_title

        if found or info.web_page or info.title:
            return info
        return None

    def _parse_expire(self, val: str) -> str:
        from datetime import datetime
        try:
            ts = int(val)
            if ts > 0:
                dt = datetime.fromtimestamp(ts)
                return dt.strftime("%Y-%m-%d")
        except Exception:
            pass
        return val

    def fetch_async(self, url: str, callback: Callable):
        def _worker():
            servers, sub_info = self.fetch_subscription(url)
            callback(servers, sub_info)

        threading.Thread(target=_worker, daemon=True).start()

    def update_all(self, subscriptions: List[dict], callback: Callable):
        def _worker():
            for sub in subscriptions:
                if not sub.get("enabled", True):
                    continue
                url = sub["url"]
                servers, sub_info = self.fetch_subscription(url)
                for s in servers:
                    s.subscription_name = sub.get("name", "")
                callback(url, servers, sub_info)

        threading.Thread(target=_worker, daemon=True).start()

    def fetch_traffic_info(self, url: str) -> Optional[SubscriptionInfo]:
        try:
            headers = {
                "User-Agent": "VPNClient/1.0",
            }
            response = requests.head(url, headers=headers, timeout=10)
            return self._parse_subscription_headers(response.headers)
        except Exception:
            return None