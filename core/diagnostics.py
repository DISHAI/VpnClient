

import socket
import subprocess
import platform
import threading
import time
import os
from typing import Callable
from utils.logger import get_logger


class DiagnosticsManager:
    def __init__(self):
        self.logger = get_logger()

    def run_full_diagnostics(self, server, config, callback, done_callback):
        def _run():
            try:
                if server.server_type == "hysteria2":
                    from core.hysteria_client import HysteriaClient
                    client = HysteriaClient(config)
                    client.generate_config(server)
                elif server.server_type == "vless":
                    from core.vless_client import VLESSClient
                    client = VLESSClient(config)
                    client.generate_config(server)
            except Exception as e:
                callback("Генерация конфига", f"❌ Ошибка: {e}")

            callback("Системная информация", self.get_system_info())
            callback("TCP Ping", self._test_tcp(server.address, server.port))
            callback("Бинарник", self._check_binary(server.server_type, config))
            callback("Конфиг", self._check_config(server.server_type, config))
            callback("Тест подключения", self._test_connection_verbose(server, config))
            done_callback()

        threading.Thread(target=_run, daemon=True).start()

    def _test_tcp(self, host: str, port: int, timeout: int = 5) -> str:
        try:
            start = time.time()
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex((host, port))
            elapsed = int((time.time() - start) * 1000)
            sock.close()

            if result == 0:
                return f"✅ TCP порт {port} открыт ({elapsed}ms)"
            else:
                return (
                    f"❌ TCP порт {port} закрыт (код: {result})\n"
                    f"   Hysteria2 использует UDP/QUIC — TCP может быть закрыт специально."
                )
        except socket.timeout:
            return f"❌ TCP таймаут к {host}:{port}"
        except socket.gaierror as e:
            return f"❌ DNS ошибка: {host}\n   {e}"
        except Exception as e:
            return f"❌ TCP ошибка: {e}"

    def _check_binary(self, server_type: str, config) -> str:
        results = []

        if server_type == "hysteria2":
            custom = config.settings.get("hysteria_binary", "")
            if custom:
                if os.path.isfile(custom):
                    results.append(f"✅ Путь: {custom}")
                    results.append(f"   Версия: {self._get_version(custom)}")
                else:
                    results.append(f"❌ Путь не найден: {custom}")

            found = self._which("hysteria") or self._which("hysteria2")
            if found:
                results.append(f"✅ В PATH: {found}")
                results.append(f"   Версия: {self._get_version(found)}")
            else:
                results.append("❌ Hysteria2 не найден в PATH")
                results.append("   bash <(curl -fsSL https://get.hy2.sh/)")

        elif server_type == "vless":
            custom = config.settings.get("xray_binary", "")
            if custom:
                if os.path.isfile(custom):
                    results.append(f"✅ Путь: {custom}")
                    results.append(f"   Версия: {self._get_version(custom)}")
                else:
                    results.append(f"❌ Путь не найден: {custom}")

            found = self._which("xray")
            if found:
                results.append(f"✅ В PATH: {found}")
                results.append(f"   Версия: {self._get_version(found)}")
            else:
                results.append("❌ Xray не найден в PATH")

        return "\n".join(results) if results else "⚠️ Неизвестный тип"

    def _check_config(self, server_type: str, config) -> str:
        results = []

        if server_type == "hysteria2":
            config_path = os.path.join(config.CONFIG_DIR, "hysteria", "config.yaml")
        else:
            config_path = os.path.join(config.CONFIG_DIR, "xray", "config.json")

        if os.path.isfile(config_path):
            results.append(f"✅ Конфиг: {config_path}")
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                results.append(f"\n{content}")
            except Exception as e:
                results.append(f"❌ Ошибка чтения: {e}")
        else:
            results.append(f"❌ Не найден: {config_path}")

        return "\n".join(results)

    def _test_connection_verbose(self, server, config) -> str:
        if server.server_type != "hysteria2":
            return "ℹ️ Тестовое подключение только для Hysteria2"

        results = []
        binary = (
            config.settings.get("hysteria_binary", "")
            or self._which("hysteria")
            or self._which("hysteria2")
            or "hysteria"
        )

        config_path = os.path.join(config.CONFIG_DIR, "hysteria", "config.yaml")
        if not os.path.isfile(config_path):
            return "❌ Конфиг не найден"

        results.append(f"Запуск: {binary} client -c {config_path}")
        results.append("Ждём 12 секунд...\n")

        try:
            startupinfo = None
            if platform.system() == "Windows":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW

            proc = subprocess.Popen(
                [binary, "client", "-c", config_path],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                startupinfo=startupinfo,
            )

            output_lines = []

            def _read(pipe):
                for line in iter(pipe.readline, b''):
                    text = line.decode('utf-8', errors='replace').strip()
                    if text:
                        output_lines.append(text)

            t1 = threading.Thread(target=_read, args=(proc.stdout,), daemon=True)
            t2 = threading.Thread(target=_read, args=(proc.stderr,), daemon=True)
            t1.start()
            t2.start()

            time.sleep(12)

            try:
                proc.terminate()
                proc.wait(timeout=3)
            except Exception:
                proc.kill()

            results.extend(output_lines)

            full_output = "\n".join(output_lines).lower()
            results.append("\n--- Анализ ---")

            if "timeout" in full_output and "handshake" in full_output:
                results.append("❌ UDP/QUIC handshake таймаут")
                results.append("   • Сервер недоступен или упал")
                results.append("   • Файрвол блокирует UDP")
                results.append("   • Неправильный порт/адрес/пароль")
                results.append("   • ISP блокирует QUIC")
            elif "connected" in full_output:
                results.append("✅ Подключение установлено!")
            elif "auth" in full_output and "failed" in full_output:
                results.append("❌ Неправильный пароль")
            elif "certificate" in full_output or "tls" in full_output:
                results.append("❌ Ошибка TLS/сертификата — включите insecure")

        except FileNotFoundError:
            results.append(f"❌ Не найден: {binary}")
        except Exception as e:
            results.append(f"❌ Ошибка: {e}")

        return "\n".join(results)

    def _which(self, name: str) -> str:
        try:
            if platform.system() == "Windows":
                result = subprocess.run(["where", name], capture_output=True, text=True, timeout=5)
            else:
                result = subprocess.run(["which", name], capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                return result.stdout.strip().split("\n")[0].strip()
        except Exception:
            pass
        return ""

    def _get_version(self, binary: str) -> str:
        for flag in ["version", "--version", "-v"]:
            try:
                result = subprocess.run([binary, flag], capture_output=True, text=True, timeout=5)
                out = (result.stdout + result.stderr).strip()
                if out:
                    return out.split("\n")[0].strip()
            except Exception:
                continue
        return "неизвестно"

    def get_system_info(self) -> str:
        import sys
        lines = [
            f"OS: {platform.system()} {platform.release()} {platform.machine()}",
            f"Python: {sys.version.split()[0]}",
        ]
        for tool in ["hysteria", "hysteria2", "xray"]:
            path = self._which(tool)
            if path:
                lines.append(f"{tool}: {path} ({self._get_version(path)})")
            else:
                lines.append(f"{tool}: не найден")
        return "\n".join(lines)