

import platform
import subprocess
import os
from utils.logger import get_logger


class SystemProxyManager:
    
    
    def __init__(self):
        self.logger = get_logger()
        self.system = platform.system()
        self._original_proxy = None
    
    def set_proxy(self, http_port: int, socks_port: int):
        
        try:
            if self.system == "Windows":
                self._set_windows_proxy(http_port)
            elif self.system == "Darwin":
                self._set_macos_proxy(http_port, socks_port)
            elif self.system == "Linux":
                self._set_linux_proxy(http_port, socks_port)
            
            self.logger.info(f"Системный прокси установлен (HTTP:{http_port}, SOCKS:{socks_port})")
        except Exception as e:
            self.logger.error(f"Ошибка установки системного прокси: {e}")
    
    def unset_proxy(self):
        
        try:
            if self.system == "Windows":
                self._unset_windows_proxy()
            elif self.system == "Darwin":
                self._unset_macos_proxy()
            elif self.system == "Linux":
                self._unset_linux_proxy()
            
            self.logger.info("Системный прокси снят")
        except Exception as e:
            self.logger.error(f"Ошибка снятия системного прокси: {e}")
    
    def _set_windows_proxy(self, http_port: int):
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 1)
        winreg.SetValueEx(key, "ProxyServer", 0, winreg.REG_SZ, f"127.0.0.1:{http_port}")
        winreg.SetValueEx(key, "ProxyOverride", 0, winreg.REG_SZ, 
                         "localhost;127.*;10.*;172.16.*;172.17.*;172.18.*;172.19.*;172.20.*;"
                         "172.21.*;172.22.*;172.23.*;172.24.*;172.25.*;172.26.*;172.27.*;"
                         "172.28.*;172.29.*;172.30.*;172.31.*;192.168.*")
        winreg.CloseKey(key)
    
    def _unset_windows_proxy(self):
        import winreg
        key = winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
            0, winreg.KEY_SET_VALUE
        )
        winreg.SetValueEx(key, "ProxyEnable", 0, winreg.REG_DWORD, 0)
        winreg.CloseKey(key)
    
    def _set_macos_proxy(self, http_port: int, socks_port: int):
        services = self._get_macos_network_services()
        for service in services:
            subprocess.run([
                "networksetup", "-setwebproxy", service,
                "127.0.0.1", str(http_port)
            ], capture_output=True)
            subprocess.run([
                "networksetup", "-setsecurewebproxy", service,
                "127.0.0.1", str(http_port)
            ], capture_output=True)
            subprocess.run([
                "networksetup", "-setsocksfirewallproxy", service,
                "127.0.0.1", str(socks_port)
            ], capture_output=True)
    
    def _unset_macos_proxy(self):
        services = self._get_macos_network_services()
        for service in services:
            subprocess.run(["networksetup", "-setwebproxystate", service, "off"],
                         capture_output=True)
            subprocess.run(["networksetup", "-setsecurewebproxystate", service, "off"],
                         capture_output=True)
            subprocess.run(["networksetup", "-setsocksfirewallproxystate", service, "off"],
                         capture_output=True)
    
    def _get_macos_network_services(self):
        result = subprocess.run(
            ["networksetup", "-listallnetworkservices"],
            capture_output=True, text=True
        )
        services = []
        for line in result.stdout.strip().split("\n")[1:]:
            line = line.strip()
            if line and not line.startswith("*"):
                services.append(line)
        return services
    
    def _set_linux_proxy(self, http_port: int, socks_port: int):
        try:
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy", "mode", "manual"
            ], capture_output=True)
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.http", "host", "127.0.0.1"
            ], capture_output=True)
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.http", "port", str(http_port)
            ], capture_output=True)
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.https", "host", "127.0.0.1"
            ], capture_output=True)
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.https", "port", str(http_port)
            ], capture_output=True)
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.socks", "host", "127.0.0.1"
            ], capture_output=True)
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy.socks", "port", str(socks_port)
            ], capture_output=True)
        except Exception:
            pass
    
    def _unset_linux_proxy(self):
        try:
            subprocess.run([
                "gsettings", "set", "org.gnome.system.proxy", "mode", "none"
            ], capture_output=True)
        except Exception:
            pass