

import time
import socket
import threading
from typing import Optional, Callable
from core.server import ServerConfig
from core.config import AppConfig
from core.hysteria_client import HysteriaClient
from core.vless_client import VLESSClient
from core.tun_manager import SystemProxyManager
from utils.logger import get_logger
from core.singbox_client import SingBoxClient


class ConnectionState:
    DISCONNECTED = "disconnected"
    CONNECTING = "connecting"
    CONNECTED = "connected"
    DISCONNECTING = "disconnecting"
    ERROR = "error"


class ConnectionManager:
    def __init__(self, config: AppConfig):
        self.config = config
        self.logger = get_logger()
        self.hysteria = HysteriaClient(config)
        self.vless = VLESSClient(config)
        self.singbox = SingBoxClient(config)
        self.proxy_manager = SystemProxyManager()

        self.state = ConnectionState.DISCONNECTED
        self.current_server: Optional[ServerConfig] = None
        self.connect_time: float = 0
        self.state_callbacks: list = []
        self._monitor_thread: Optional[threading.Thread] = None
        self._monitoring = False
        self._lock = threading.Lock()

    def add_state_callback(self, callback: Callable[[str], None]):
        self.state_callbacks.append(callback)

    def _notify_state(self, state: str):
        self.state = state
        for cb in self.state_callbacks:
            try:
                cb(state)
            except Exception:
                pass

    def connect(self, server: ServerConfig):
        
        with self._lock:
            if self.state in (ConnectionState.CONNECTING, ConnectionState.CONNECTED):
                self._stop_client()
                self._monitoring = False
                if self.current_server:
                    self.current_server.is_active = False

            self.state = ConnectionState.CONNECTING
            self.current_server = server

        self._notify_state(ConnectionState.CONNECTING)

        use_tun = self.config.settings.get("tun_mode", False)
        use_singbox = self.config.settings.get("use_singbox", False)

        def _connect_worker():
            try:
                success = False
                mode_str = "TUN" if use_tun else "Proxy"
                backend = "sing-box" if use_singbox else "legacy"
                
                self.logger.info(f"Подключение к {server.display_name()}")
                self.logger.info(f"Режим: {mode_str}, Бэкенд: {backend}")

                if use_singbox:
                    success = self.singbox.start(server, use_tun=use_tun, timeout=45)
                else:
                    if use_tun:
                        self.logger.error("TUN режим требует sing-box. Включите 'Использовать sing-box' в настройках")
                        self._notify_state(ConnectionState.ERROR)
                        return
                    
                    if server.server_type == "hysteria2":
                        success = self.hysteria.start(server, timeout=45)
                    elif server.server_type == "vless":
                        success = self.vless.start(server)
                    else:
                        self.logger.error(f"Неизвестный тип: {server.server_type}")
                        self._notify_state(ConnectionState.ERROR)
                        return

                if not success:
                    self._notify_state(ConnectionState.ERROR)
                    return

                self.logger.info("Проверка готовности...")
                
                if use_tun:
                    time.sleep(2)
                    self.connect_time = time.time()
                    server.is_active = True
                    self._notify_state(ConnectionState.CONNECTED)
                    self._start_monitoring()
                    self.logger.info(f"✓ TUN подключение установлено")
                    self.logger.info("Весь трафик идёт через VPN туннель")
                else:
                    if self._check_proxy_ready(retries=10, delay=1):
                        self.connect_time = time.time()
                        server.is_active = True
                        
                        if self.config.settings.get("system_proxy", True) and not use_singbox:
                            self.proxy_manager.set_proxy(
                                self.config.settings["http_port"],
                                self.config.settings["socks_port"]
                            )
                        
                        self._notify_state(ConnectionState.CONNECTED)
                        self._start_monitoring()
                        self.logger.info(f"✓ Прокси готов")
                        self.logger.info(f"  SOCKS5: 127.0.0.1:{self.config.settings['socks_port']}")
                        self.logger.info(f"  HTTP: 127.0.0.1:{self.config.settings['http_port']}")
                    else:
                        self.logger.error("Прокси не готов")
                        self._stop_client()
                        self._notify_state(ConnectionState.ERROR)

            except Exception as e:
                self.logger.error(f"Ошибка подключения: {e}")
                import traceback
                self.logger.debug(traceback.format_exc())
                self._notify_state(ConnectionState.ERROR)

        threading.Thread(target=_connect_worker, daemon=True).start()

    def disconnect(self):
        self._notify_state(ConnectionState.DISCONNECTING)
        self._monitoring = False

        if self.config.settings.get("system_proxy", True):
            self.proxy_manager.unset_proxy()

        self._stop_client()

        if self.current_server:
            self.current_server.is_active = False

        self.current_server = None
        self.connect_time = 0
        self._notify_state(ConnectionState.DISCONNECTED)
        self.logger.info("Отключено")

    def _stop_client(self):
        
        if self.singbox.is_running():
            self.singbox.stop()
        if self.hysteria.is_running():
            self.hysteria.stop()
        if self.vless.is_running():
            self.vless.stop()

    def _check_proxy_ready(self, retries: int = 10, delay: float = 1) -> bool:
        port = self.config.settings["socks_port"]
        for i in range(retries):
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(2)
                result = sock.connect_ex(("127.0.0.1", port))
                sock.close()
                if result == 0:
                    return True
            except Exception:
                pass
            time.sleep(delay)
        return False

    def _start_monitoring(self):
        
        self._monitoring = True
        use_singbox = self.config.settings.get("use_singbox", False)

        def _monitor():
            while self._monitoring:
                time.sleep(5)
                if not self._monitoring:
                    break

                running = False
                if self.current_server:
                    if use_singbox:
                        running = self.singbox.is_running()
                    elif self.current_server.server_type == "hysteria2":
                        running = self.hysteria.is_running()
                    elif self.current_server.server_type == "vless":
                        running = self.vless.is_running()

                if not running and self.state == ConnectionState.CONNECTED:
                    self.logger.warning("VPN процесс завершился")
                    if not self.config.settings.get("use_singbox", False):
                        if self.config.settings.get("system_proxy", True):
                            self.proxy_manager.unset_proxy()
                    if self.current_server:
                        self.current_server.is_active = False
                    self._notify_state(ConnectionState.ERROR)
                    self._monitoring = False

        self._monitor_thread = threading.Thread(target=_monitor, daemon=True)
        self._monitor_thread.start()

    def get_connection_duration(self) -> str:
        if self.connect_time == 0:
            return "00:00:00"

        elapsed = int(time.time() - self.connect_time)
        hours = elapsed // 3600
        minutes = (elapsed % 3600) // 60
        seconds = elapsed % 60
        return f"{hours:02d}:{minutes:02d}:{seconds:02d}"

    def test_latency(self, server: ServerConfig, callback: Callable[[int], None]):
        def _test():
            try:
                latencies = []
                for i in range(3):
                    try:
                        latency = self._ping_tcp(server)
                        if latency >= 0:
                            latencies.append(latency)
                    except Exception:
                        pass
                    time.sleep(0.1)

                if latencies:
                    avg_latency = sum(latencies) // len(latencies)
                    server.latency = avg_latency
                    self.logger.info(f"Ping {server.display_name()}: {avg_latency}ms")
                    callback(avg_latency)
                else:
                    server.latency = -1
                    self.logger.warning(f"Ping {server.display_name()}: timeout")
                    callback(-1)
            except Exception:
                server.latency = -1
                callback(-1)

        threading.Thread(target=_test, daemon=True).start()

    def _ping_tcp(self, server: ServerConfig) -> int:
        
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(5)
        try:
            start = time.time()
            sock.connect((server.address, server.port))
            return int((time.time() - start) * 1000)
        finally:
            sock.close()

    def is_connected(self) -> bool:
        return self.state == ConnectionState.CONNECTED