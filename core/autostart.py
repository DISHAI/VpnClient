

import platform
import sys
import os
from utils.logger import get_logger

APP_NAME = "VPNClient"


class AutostartManager:
    

    def __init__(self):
        self.logger = get_logger()
        self.system = platform.system()

    def is_enabled(self) -> bool:
        
        try:
            if self.system == "Windows":
                return self._is_enabled_windows()
            elif self.system == "Darwin":
                return self._is_enabled_macos()
            elif self.system == "Linux":
                return self._is_enabled_linux()
        except Exception as e:
            self.logger.error(f"Ошибка проверки автозапуска: {e}")
        return False

    def enable(self) -> bool:
        
        try:
            if self.system == "Windows":
                return self._enable_windows()
            elif self.system == "Darwin":
                return self._enable_macos()
            elif self.system == "Linux":
                return self._enable_linux()
        except Exception as e:
            self.logger.error(f"Ошибка включения автозапуска: {e}")
        return False

    def disable(self) -> bool:
        
        try:
            if self.system == "Windows":
                return self._disable_windows()
            elif self.system == "Darwin":
                return self._disable_macos()
            elif self.system == "Linux":
                return self._disable_linux()
        except Exception as e:
            self.logger.error(f"Ошибка отключения автозапуска: {e}")
        return False

    def _startup_dir(self) -> str:
        return os.path.join(
            os.environ["APPDATA"],
            r"Microsoft\Windows\Start Menu\Programs\Startup"
        )

    def _vbs_path(self) -> str:
        return os.path.join(self._startup_dir(), f"{APP_NAME}.vbs")

    def _get_exe_path(self) -> str:
        if getattr(sys, 'frozen', False):
            return sys.executable
        return sys.executable

    def _is_enabled_windows(self) -> bool:
        return os.path.isfile(self._vbs_path())

    def _enable_windows(self) -> bool:
        exe = self._get_exe_path()
        vbs_content = f'Set WshShell = CreateObject("WScript.Shell")\nWshShell.Run """{exe}"" --autostart", 0, False\n'
        try:
            with open(self._vbs_path(), 'w') as f:
                f.write(vbs_content)
            self._remove_old_autostart()
            self.logger.info("Автозапуск включён (Windows, Startup)")
            return True
        except Exception as e:
            self.logger.error(f"Ошибка создания автозапуска: {e}")
            return False

    def _disable_windows(self) -> bool:
        try:
            path = self._vbs_path()
            if os.path.isfile(path):
                os.remove(path)
            self._remove_old_autostart()
            self.logger.info("Автозапуск отключён (Windows)")
        except Exception as e:
            self.logger.error(f"Ошибка отключения автозапуска: {e}")
        return True

    def _remove_old_autostart(self):
        
        try:
            import winreg
            key = winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Run",
                0, winreg.KEY_SET_VALUE
            )
            winreg.DeleteValue(key, APP_NAME)
            winreg.CloseKey(key)
        except FileNotFoundError:
            pass
        try:
            import subprocess
            subprocess.run(
                ["schtasks", "/delete", "/tn", "VPNClient_Autostart", "/f"],
                capture_output=True
            )
        except Exception:
            pass

    def _plist_path(self) -> str:
        return os.path.expanduser(
            f"~/Library/LaunchAgents/com.vpnclient.autostart.plist"
        )

    def _is_enabled_macos(self) -> bool:
        return os.path.isfile(self._plist_path())

    def _enable_macos(self) -> bool:
        plist = self._plist_path()
        exe = sys.executable if getattr(sys, 'frozen', False) else sys.executable
        args = " ".join(f'"{a}"' for a in sys.argv)

        content = f
        with open(plist, 'w') as f:
            f.write(content)
        self.logger.info("Автозапуск включён (macOS)")
        return True

    def _disable_macos(self) -> bool:
        plist = self._plist_path()
        if os.path.isfile(plist):
            os.remove(plist)
        self.logger.info("Автозапуск отключён (macOS)")
        return True

    def _desktop_file_path(self) -> str:
        return os.path.expanduser(
            "~/.config/autostart/vpnclient.desktop"
        )

    def _is_enabled_linux(self) -> bool:
        return os.path.isfile(self._desktop_file_path())

    def _enable_linux(self) -> bool:
        path = self._desktop_file_path()
        os.makedirs(os.path.dirname(path), exist_ok=True)
        exe = sys.executable if not getattr(sys, 'frozen', False) else sys.executable
        args = " ".join(sys.argv)

        content = f
        with open(path, 'w') as f:
            f.write(content)
        self.logger.info("Автозапуск включён (Linux)")
        return True

    def _disable_linux(self) -> bool:
        path = self._desktop_file_path()
        if os.path.isfile(path):
            os.remove(path)
        self.logger.info("Автозапуск отключён (Linux)")
        return True
