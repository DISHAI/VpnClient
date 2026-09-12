

import json
import os
import subprocess
import signal
import threading
import time
import platform
from typing import Optional
from core.server import ServerConfig
from core.config import AppConfig
from utils.logger import get_logger


class VLESSClient:
    
    
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger()
        self.process: Optional[subprocess.Popen] = None
        self.config_dir = os.path.join(config.CONFIG_DIR, "xray")
        os.makedirs(self.config_dir, exist_ok=True)
        self._connected = False
        self._error_message = ""
    
    def _find_binary(self) -> str:
        
        custom = self.config.settings.get("xray_binary", "")
        if custom and os.path.isfile(custom):
            return custom
        
        names = ["xray", "xray-linux-amd64", "xray-linux-arm64"]
        if platform.system() == "Windows":
            names = ["xray.exe", "xray-windows-amd64.exe"]
        elif platform.system() == "Darwin":
            names = ["xray", "xray-macos-arm64", "xray-macos-amd64"]
        
        for name in names:
            for path_dir in os.environ.get("PATH", "").split(os.pathsep):
                full = os.path.join(path_dir, name)
                if os.path.isfile(full):
                    return full
        
        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name in names:
            for d in ["bin", ".", "binaries"]:
                full = os.path.join(app_dir, d, name)
                if os.path.isfile(full):
                    return full
        
        standard_paths = [
            "/usr/local/bin/xray",
            "/usr/bin/xray",
            os.path.expanduser("~/.local/bin/xray"),
        ]
        for path in standard_paths:
            if os.path.isfile(path):
                return path
        
        return "xray"
    
    def generate_config(self, server: ServerConfig) -> str:
        
        config_path = os.path.join(self.config_dir, "config.json")
        
        vnext_user = {
            "id": server.uuid,
            "encryption": server.encryption or "none",
        }
        
        if server.flow and server.security in ("reality", "tls"):
            vnext_user["flow"] = server.flow
        
        outbound = {
            "tag": "proxy",
            "protocol": "vless",
            "settings": {
                "vnext": [{
                    "address": server.address,
                    "port": server.port,
                    "users": [vnext_user]
                }]
            },
            "streamSettings": self._build_stream_settings(server)
        }
        
        config = {
            "log": {
                "loglevel": "warning",
                "access": os.path.join(self.config_dir, "access.log"),
                "error": os.path.join(self.config_dir, "error.log"),
            },
            "inbounds": [
                {
                    "tag": "socks-in",
                    "protocol": "socks",
                    "listen": "127.0.0.1",
                    "port": self.config.settings["socks_port"],
                    "settings": {
                        "auth": "noauth",
                        "udp": True,
                        "userLevel": 0
                    },
                    "sniffing": {
                        "enabled": True,
                        "destOverride": ["http", "tls"]
                    }
                },
                {
                    "tag": "http-in",
                    "protocol": "http",
                    "listen": "127.0.0.1",
                    "port": self.config.settings["http_port"],
                    "settings": {
                        "userLevel": 0
                    }
                }
            ],
            "outbounds": [
                outbound,
                {
                    "tag": "direct",
                    "protocol": "freedom",
                    "settings": {}
                },
                {
                    "tag": "block",
                    "protocol": "blackhole",
                    "settings": {}
                }
            ],
            "routing": {
                "domainStrategy": "AsIs",
                "rules": []
            }
        }

        bypass_domains = self.config.get_bypass_domains()
        if bypass_domains:
            config["routing"]["rules"].append({
                "type": "field",
                "domain": bypass_domains,
                "outboundTag": "direct"
            })

        config["routing"]["rules"].append({
            "type": "field",
            "ip": ["geoip:private"],
            "outboundTag": "direct"
        })
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2)
        
        self.logger.debug(f"Xray конфиг сохранён: {config_path}")
        return config_path
    
    def _build_stream_settings(self, server: ServerConfig) -> dict:
        
        stream = {
            "network": server.transport or "tcp",
        }
        
        if server.security == "tls":
            stream["security"] = "tls"
            tls_settings = {
                "serverName": server.sni or server.address,
                "fingerprint": server.fingerprint or "chrome",
                "allowInsecure": server.insecure,
            }
            if server.alpn:
                tls_settings["alpn"] = [a.strip() for a in server.alpn.split(",") if a.strip()]
            stream["tlsSettings"] = tls_settings
            
        elif server.security == "reality":
            stream["security"] = "reality"
            stream["realitySettings"] = {
                "serverName": server.sni or server.address,
                "fingerprint": server.fingerprint or "chrome",
                "publicKey": server.public_key,
                "shortId": server.short_id,
                "spiderX": server.spider_x or "/",
                "show": False,
            }
        else:
            stream["security"] = "none"
        
        if server.transport == "ws":
            ws = {"path": server.path or "/"}
            if server.host:
                ws["headers"] = {"Host": server.host}
            stream["wsSettings"] = ws
            
        elif server.transport == "grpc":
            stream["grpcSettings"] = {
                "serviceName": server.service_name or "",
                "multiMode": False,
            }
            
        elif server.transport == "h2":
            h2 = {"path": server.path or "/"}
            if server.host:
                h2["host"] = [server.host]
            stream["httpSettings"] = h2
            
        elif server.transport == "tcp":
            stream["tcpSettings"] = {
                "header": {"type": "none"}
            }
        
        return stream
    
    def start(self, server: ServerConfig, timeout: int = 30) -> bool:
        
        try:
            if self.process:
                self.stop()
            
            self._connected = False
            self._error_message = ""
            
            binary = self._find_binary()
            
            if not os.path.isfile(binary) and "/" not in binary and "\\" not in binary:
                try:
                    if platform.system() == "Windows":
                        result = subprocess.run(["where", binary], capture_output=True, text=True)
                    else:
                        result = subprocess.run(["which", binary], capture_output=True, text=True)
                    if result.returncode != 0:
                        self.logger.error(f"Xray бинарник не найден: {binary}")
                        self.logger.error("Установите Xray: https://github.com/XTLS/Xray-core/releases")
                        return False
                except Exception:
                    pass
            
            config_path = self.generate_config(server)
            
            self.logger.info(f"Запуск Xray: {binary}")
            self.logger.info(f"Сервер: {server.address}:{server.port}")
            
            cmd = [binary, "run", "-c", config_path]
            
            startupinfo = None
            creationflags = 0
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                creationflags = subprocess.CREATE_NO_WINDOW
            
            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
                creationflags=creationflags if platform.system() == "Windows" else 0,
            )
            
            self._start_log_reader()
            
            self.logger.info(f"Xray процесс запущен (PID: {self.process.pid})")
            
            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.process.poll() is not None:
                    self.logger.error(f"Xray процесс завершился с кодом: {self.process.returncode}")
                    return False
                
                if self._connected:
                    return True
                
                if self._error_message:
                    self.logger.error(f"Ошибка Xray: {self._error_message}")
                    self.stop()
                    return False
                
                if self._check_port_open():
                    self._connected = True
                    self.logger.info("Xray готов к работе")
                    return True
                
                time.sleep(0.5)
            
            self.logger.error("Таймаут ожидания Xray")
            self.stop()
            return False
            
        except FileNotFoundError as e:
            self.logger.error(f"Xray бинарник не найден: {e}")
            self.logger.error("Установите Xray:")
            self.logger.error("  Linux: bash -c \"$(curl -L https://github.com/XTLS/Xray-install/raw/main/install-release.sh)\" @ install")
            self.logger.error("  macOS: brew install xray")
            self.logger.error("  Windows: скачайте с https://github.com/XTLS/Xray-core/releases")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка запуска Xray: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False
    
    def _check_port_open(self) -> bool:
        
        import socket
        port = self.config.settings["socks_port"]
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            return result == 0
        except Exception:
            return False
    
    def stop(self):
        
        if self.process:
            try:
                self.logger.info("Остановка Xray...")
                if platform.system() == "Windows":
                    self.process.terminate()
                else:
                    self.process.send_signal(signal.SIGTERM)
                
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.logger.warning("Принудительное завершение Xray...")
                    self.process.kill()
                    self.process.wait(timeout=2)
                
                self.logger.info("Xray остановлен")
            except Exception as e:
                self.logger.error(f"Ошибка остановки Xray: {e}")
            finally:
                self.process = None
                self._connected = False
    
    def is_running(self) -> bool:
        if self.process is None:
            return False
        return self.process.poll() is None
    
    def _start_log_reader(self):
        def _reader(pipe, is_stderr: bool):
            try:
                for line in iter(pipe.readline, b''):
                    if not line:
                        break
                    text = line.decode('utf-8', errors='replace').strip()
                    if not text:
                        continue
                    
                    text_lower = text.lower()
                    
                    if "started" in text_lower or "listening" in text_lower:
                        self._connected = True
                        self.logger.info(f"[Xray] {text}")
                    elif "fatal" in text_lower:
                        self._error_message = text
                        self.logger.error(f"[Xray] {text}")
                    elif "error" in text_lower or "failed" in text_lower:
                        self.logger.warning(f"[Xray] {text}")
                    elif "warning" in text_lower or "warn" in text_lower:
                        self.logger.warning(f"[Xray] {text}")
                    else:
                        self.logger.debug(f"[Xray] {text}")
            except Exception as e:
                self.logger.debug(f"Log reader error: {e}")
        
        if self.process:
            threading.Thread(
                target=_reader, args=(self.process.stdout, False), daemon=True
            ).start()
            threading.Thread(
                target=_reader, args=(self.process.stderr, True), daemon=True
            ).start()