

import uuid as _uuid
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any


@dataclass
class ServerConfig:
    id: str = field(default_factory=lambda: str(_uuid.uuid4()))
    name: str = ""
    server_type: str = "vless"
    address: str = ""
    port: int = 443

    uuid: str = ""
    flow: str = ""
    encryption: str = "none"
    transport: str = "tcp"
    security: str = "tls"
    sni: str = ""
    fingerprint: str = "chrome"
    public_key: str = ""
    short_id: str = ""
    spider_x: str = ""
    path: str = ""
    host: str = ""
    service_name: str = ""
    alpn: str = ""

    auth: str = ""
    obfs: str = ""
    obfs_password: str = ""
    insecure: bool = False

    subscription_url: str = ""
    subscription_name: str = ""

    latency: int = -1
    is_active: bool = False
    
    traffic_up: int = 0
    traffic_down: int = 0
    
    sub_traffic_used: int = 0
    sub_traffic_total: int = 0
    sub_expiry: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ServerConfig':
        valid_fields = {f.name for f in cls.__dataclass_fields__.values()}
        filtered = {k: v for k, v in data.items() if k in valid_fields}
        return cls(**filtered)

    def display_name(self) -> str:
        if self.name:
            return self.name
        return f"{self.address}:{self.port}"

    def type_badge(self) -> str:
        return self.server_type.upper()

    def latency_str(self) -> str:
        if self.latency < 0:
            return "—"
        return f"{self.latency}ms"