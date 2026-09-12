

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


class SingBoxClient:
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger()
        self.process: Optional[subprocess.Popen] = None
        self.config_dir = os.path.join(config.CONFIG_DIR, "sing-box")
        os.makedirs(self.config_dir, exist_ok=True)
        self._connected = False
        self._error_message = ""

    def _find_binary(self) -> str:
        custom = self.config.settings.get("singbox_binary", "")
        if custom and os.path.isfile(custom):
            return custom

        names = ["sing-box"]
        if platform.system() == "Windows":
            names = ["sing-box.exe"]

        for name in names:
            for path_dir in os.environ.get("PATH", "").split(os.pathsep):
                full = os.path.join(path_dir, name)
                if os.path.isfile(full):
                    return full

        app_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        for name in names:
            for subdir in ["bin", ".", "binaries"]:
                full = os.path.join(app_dir, subdir, name)
                if os.path.isfile(full):
                    return full

        return "sing-box"

    def generate_config(self, server: ServerConfig, use_tun: bool = False) -> str:
        
        config_path = os.path.join(self.config_dir, "config.json")

        outbounds = self._build_outbound(server)
        inbounds = self._build_inbounds(use_tun)
        dns_server = self.config.settings.get("dns_server", "8.8.8.8")

        route_rules = [
            {"action": "sniff"},
            {"protocol": "dns", "action": "hijack-dns"},
        ]

        bypass_domains = self.config.get_bypass_domains()
        if bypass_domains:
            clean = []
            for d in bypass_domains:
                d = d.strip().lower()
                d = d.replace("https://", "").replace("http://", "")
                d = d.split("/")[0]
                d = d.split(":")[0]
                if d:
                    clean.append(d)
            if clean:
                route_rules.append({
                    "domain_suffix": clean,
                    "outbound": "direct"
                })

        route_rules.append({"ip_is_private": True, "outbound": "direct"})

        config = {
            "log": {
                "level": "info",
                "timestamp": True
            },
            "dns": {
                "servers": [
                    {
                        "tag": "dns-remote",
                        "type": "udp",
                        "server": dns_server,
                    },
                    {
                        "tag": "dns-local",
                        "type": "local",
                    }
                ],
                "rules": [],
                "strategy": "prefer_ipv4",
                "independent_cache": True
            },
            "inbounds": inbounds,
            "outbounds": outbounds + [
                {"tag": "direct", "type": "direct"},
                {"tag": "block", "type": "block"}
            ],
            "route": {
                "rules": route_rules,
                "auto_detect_interface": True,
                "final": "proxy",
                "default_domain_resolver": "dns-remote"
            }
        }

        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)

        self.logger.debug(f"sing-box конфиг: {config_path}")
        return config_path


    def _build_inbounds(self, use_tun: bool) -> list:
        if use_tun:
            tun_inbound = {
                "type": "tun",
                "tag": "tun-in",
                "address": [
                    "172.19.0.1/30"
                ],
                "mtu": 1500,
                "auto_route": True,
                "strict_route": True,
                "stack": "system"
            }

            if platform.system() == "Windows":
                tun_inbound["interface_name"] = "SafeVPN"
            else:
                tun_inbound["interface_name"] = "utun8"

            return [tun_inbound]
        else:
            return [
                {
                    "type": "socks",
                    "tag": "socks-in",
                    "listen": "127.0.0.1",
                    "listen_port": self.config.settings["socks_port"]
                },
                {
                    "type": "http",
                    "tag": "http-in",
                    "listen": "127.0.0.1",
                    "listen_port": self.config.settings["http_port"]
                }
            ]

    def _build_outbound(self, server: ServerConfig) -> list:
        if server.server_type == "vless":
            return self._build_vless_outbound(server)
        elif server.server_type == "hysteria2":
            return self._build_hysteria2_outbound(server)
        else:
            raise ValueError(f"Unsupported: {server.server_type}")

    def _build_vless_outbound(self, server: ServerConfig) -> list:
        outbound = {
            "type": "vless",
            "tag": "proxy",
            "server": server.address,
            "server_port": server.port,
            "uuid": server.uuid,
            "packet_encoding": "xudp"
        }

        if server.flow:
            outbound["flow"] = server.flow

        if server.transport and server.transport != "tcp":
            transport = {"type": server.transport}
            if server.transport == "ws":
                transport["path"] = server.path or "/"
                if server.host:
                    transport["headers"] = {"Host": server.host}
            elif server.transport == "grpc":
                transport["service_name"] = server.service_name or ""
            elif server.transport in ("http", "h2"):
                transport["type"] = "http"
                transport["path"] = server.path or "/"
                if server.host:
                    transport["host"] = [server.host]
            outbound["transport"] = transport

        if server.security == "tls":
            outbound["tls"] = {
                "enabled": True,
                "server_name": server.sni or server.address,
                "insecure": server.insecure,
                "utls": {
                    "enabled": True,
                    "fingerprint": server.fingerprint or "chrome"
                }
            }
        elif server.security == "reality":
            outbound["tls"] = {
                "enabled": True,
                "server_name": server.sni or server.address,
                "reality": {
                    "enabled": True,
                    "public_key": server.public_key,
                    "short_id": server.short_id
                },
                "utls": {
                    "enabled": True,
                    "fingerprint": server.fingerprint or "chrome"
                }
            }

        return [outbound]

    def _build_hysteria2_outbound(self, server: ServerConfig) -> list:
        outbound = {
            "type": "hysteria2",
            "tag": "proxy",
            "server": server.address,
            "server_port": server.port,
            "password": server.auth,
            "tls": {
                "enabled": True,
                "server_name": server.sni or server.address,
                "insecure": server.insecure
            }
        }

        if server.obfs and server.obfs_password:
            outbound["obfs"] = {
                "type": server.obfs,
                "password": server.obfs_password
            }

        return [outbound]

    def start(self, server: ServerConfig, use_tun: bool = False, timeout: int = 30) -> bool:
        if use_tun and platform.system() == "Windows":
            import ctypes
            try:
                is_admin = ctypes.windll.shell32.IsUserAnAdmin() != 0
            except Exception:
                is_admin = False
            if not is_admin:
                self.logger.error("TUN-режим требует запуска от имени администратора!")
                return False

        try:
            if self.process:
                self.stop()

            self._connected = False
            self._error_message = ""

            binary = self._find_binary()

            if not os.path.isfile(binary) and "/" not in binary and "\\" not in binary:
                self.logger.error(f"sing-box не найден: {binary}")
                return False

            config_path = self.generate_config(server, use_tun)

            mode_str = "TUN" if use_tun else "Proxy"
            self.logger.info(f"Запуск sing-box ({mode_str}): {binary}")

            cmd = [binary, "run", "-c", config_path, "-D", self.config_dir]

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

            self.logger.info(f"sing-box запущен (PID: {self.process.pid})")

            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.process.poll() is not None:
                    self.logger.error(f"sing-box завершился с кодом: {self.process.returncode}")
                    if self._error_message:
                        self.logger.error(f"Ошибка: {self._error_message}")
                    return False

                if self._connected:
                    self.logger.info(f"sing-box ({mode_str}) готов")
                    return True

                if self._error_message and "fatal" in self._error_message.lower():
                    self.logger.error(f"sing-box: {self._error_message}")
                    self.stop()
                    return False

                if not use_tun and self._check_proxy_ready():
                    self._connected = True
                    return True

                time.sleep(0.5)

            if self.is_running():
                self._connected = True
                self.logger.info(f"sing-box ({mode_str}) запущен (таймаут, но процесс жив)")
                return True

            self.logger.error("Таймаут sing-box")
            self.stop()
            return False

        except Exception as e:
            self.logger.error(f"Ошибка sing-box: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False

    def _check_proxy_ready(self) -> bool:
        import socket
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(1)
            result = sock.connect_ex(("127.0.0.1", self.config.settings["socks_port"]))
            sock.close()
            return result == 0
        except Exception:
            return False

    def stop(self):
        if self.process:
            try:
                self.logger.info("Остановка sing-box...")
                if platform.system() == "Windows":
                    self.process.terminate()
                else:
                    self.process.send_signal(signal.SIGTERM)
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
                self.logger.info("sing-box остановлен")
            except Exception as e:
                self.logger.error(f"Ошибка остановки: {e}")
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

                    if any(x in text_lower for x in [
                        "tun started", "inbound/tun", "socks server started",
                        "http server started"
                    ]):
                        self._connected = True
                        self.logger.info(f"[sing-box] {text}")
                    elif "fatal" in text_lower:
                        self._error_message = text
                        self.logger.error(f"[sing-box] {text}")
                    elif "error" in text_lower or "failed" in text_lower:
                        self._error_message = text
                        self.logger.error(f"[sing-box] {text}")
                    elif "warn" in text_lower:
                        self.logger.warning(f"[sing-box] {text}")
                    else:
                        self.logger.debug(f"[sing-box] {text}")
            except Exception as e:
                self.logger.debug(f"Log reader: {e}")

        if self.process:
            threading.Thread(target=_reader, args=(self.process.stdout, False), daemon=True).start()
            threading.Thread(target=_reader, args=(self.process.stderr, True), daemon=True).start()