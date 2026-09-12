

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


class HysteriaClient:
    

    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger()
        self.process: Optional[subprocess.Popen] = None
        self.config_dir = os.path.join(config.CONFIG_DIR, "hysteria")
        os.makedirs(self.config_dir, exist_ok=True)
        self._connected = False
        self._error_message = ""
        self._connection_event = threading.Event()

    def _find_binary(self) -> str:
        custom = self.config.settings.get("hysteria_binary", "")
        if custom and os.path.isfile(custom):
            return custom

        names = ["hysteria", "hysteria2"]
        if platform.system() == "Windows":
            names = ["hysteria.exe", "hysteria2.exe", "hysteria-windows-amd64.exe", "hysteria2-windows-amd64.exe"]
        elif platform.system() == "Darwin":
            names = ["hysteria", "hysteria2", "hysteria-darwin-arm64", "hysteria-darwin-amd64"]
        else:
            names = ["hysteria", "hysteria2", "hysteria-linux-amd64", "hysteria2-linux-amd64"]

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

        standard_paths = [
            "/usr/local/bin/hysteria",
            "/usr/local/bin/hysteria2",
            "/usr/bin/hysteria",
            "/usr/bin/hysteria2",
            os.path.expanduser("~/.local/bin/hysteria"),
            os.path.expanduser("~/.local/bin/hysteria2"),
        ]
        for path in standard_paths:
            if os.path.isfile(path):
                return path

        return "hysteria"

    def generate_config(self, server: ServerConfig) -> str:
        config_path = os.path.join(self.config_dir, "config.yaml")

        config = {
            "server": f"{server.address}:{server.port}",
            "auth": server.auth,
            "tls": {
                "sni": server.sni or server.address,
                "insecure": server.insecure,
            },
            "socks5": {
                "listen": f"127.0.0.1:{self.config.settings['socks_port']}",
            },
            "http": {
                "listen": f"127.0.0.1:{self.config.settings['http_port']}",
            },
            "quic": {
                "initStreamReceiveWindow": 8388608,
                "maxStreamReceiveWindow": 8388608,
                "initConnReceiveWindow": 20971520,
                "maxConnReceiveWindow": 20971520,
                "maxIdleTimeout": "60s",
                "keepAlivePeriod": "10s",
            }
        }

        if server.obfs and server.obfs_password:
            config["obfs"] = {
                "type": server.obfs,
                "salamander": {
                    "password": server.obfs_password,
                }
            }

        import yaml
        with open(config_path, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)

        self.logger.debug(f"Hysteria2 конфиг сохранён: {config_path}")
        return config_path

    def start(self, server: ServerConfig, timeout: int = 30) -> bool:
        try:
            if self.process:
                self.stop()

            self._connected = False
            self._error_message = ""
            self._connection_event.clear()

            binary = self._find_binary()

            if not os.path.isfile(binary) and "/" not in binary and "\\" not in binary:
                try:
                    if platform.system() == "Windows":
                        result = subprocess.run(["where", binary], capture_output=True, text=True)
                    else:
                        result = subprocess.run(["which", binary], capture_output=True, text=True)
                    if result.returncode != 0:
                        self.logger.error(f"Hysteria2 не найден: {binary}")
                        self.logger.error("Установите: https://hysteria.network/docs/getting-started/Installation/")
                        return False
                except Exception:
                    pass

            config_path = self.generate_config(server)

            self.logger.info(f"Запуск Hysteria2: {binary}")
            self.logger.info(f"Сервер: {server.address}:{server.port}")

            cmd = [binary, "client", "-c", config_path]
            self.logger.debug(f"Команда: {' '.join(cmd)}")

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

            self.logger.info(f"Hysteria2 запущен (PID: {self.process.pid})")
            self.logger.info(f"Ожидание подключения (таймаут: {timeout}с)...")

            start_time = time.time()
            while time.time() - start_time < timeout:
                if self.process.poll() is not None:
                    self.logger.error(f"Hysteria2 завершился с кодом: {self.process.returncode}")
                    if self._error_message:
                        self.logger.error(f"Ошибка: {self._error_message}")
                    return False

                if self._connected:
                    self.logger.info("Hysteria2 успешно подключен")
                    return True

                if self._error_message and "FATAL" in self._error_message:
                    self.logger.error(f"Ошибка Hysteria2: {self._error_message}")
                    self.stop()
                    return False

                time.sleep(0.5)

            self.logger.warning(f"Таймаут ({timeout}с), проверяем порт...")
            if self._check_port_open():
                self._connected = True
                self.logger.info("Порт открыт, подключено")
                return True

            self.logger.error("Не удалось подключиться")
            self.stop()
            return False

        except FileNotFoundError as e:
            self.logger.error(f"Hysteria2 не найден: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Ошибка запуска Hysteria2: {e}")
            import traceback
            self.logger.debug(traceback.format_exc())
            return False

    def _check_port_open(self) -> bool:
        import socket
        port = self.config.settings["socks_port"]
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(("127.0.0.1", port))
            sock.close()
            return result == 0
        except Exception:
            return False

    def stop(self):
        if self.process:
            try:
                self.logger.info("Остановка Hysteria2...")
                if platform.system() == "Windows":
                    self.process.terminate()
                else:
                    self.process.send_signal(signal.SIGTERM)
                try:
                    self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill()
                    self.process.wait(timeout=2)
                self.logger.info("Hysteria2 остановлен")
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
                        "connected to server",
                        "client started",
                        "socks5 server listening",
                        "http proxy server listening",
                        "server listening"
                    ]):
                        self._connected = True
                        self.logger.info(f"[Hysteria2] {text}")
                    elif "fatal" in text_lower or "error" in text_lower or "failed" in text_lower:
                        self._error_message = text
                        self.logger.error(f"[Hysteria2] {text}")
                    elif "warn" in text_lower:
                        self.logger.warning(f"[Hysteria2] {text}")
                    elif "info" in text_lower:
                        self.logger.info(f"[Hysteria2] {text}")
                    else:
                        self.logger.debug(f"[Hysteria2] {text}")

            except Exception as e:
                self.logger.debug(f"Log reader error: {e}")

        if self.process:
            threading.Thread(target=_reader, args=(self.process.stdout, False), daemon=True).start()
            threading.Thread(target=_reader, args=(self.process.stderr, True), daemon=True).start()