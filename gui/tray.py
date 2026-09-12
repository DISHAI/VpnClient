

import threading
import platform
from typing import Callable, Optional
from PIL import Image, ImageDraw

try:
    import pystray
    from pystray import MenuItem, Menu

    TRAY_AVAILABLE = True
except ImportError:
    TRAY_AVAILABLE = False


class TrayIcon:
    

    def __init__(self, on_show: Callable, on_quit: Callable,
                 on_connect: Callable, on_disconnect: Callable,
                 get_status: Callable):
        self.on_show = on_show
        self.on_quit = on_quit
        self.on_connect = on_connect
        self.on_disconnect = on_disconnect
        self.get_status = get_status
        self.icon: Optional[pystray.Icon] = None
        self._running = False

        if not TRAY_AVAILABLE:
            return

    def _create_icon_image(self, connected: bool = False) -> Image.Image:
        
        size = 64
        img = Image.new('RGBA', (size, size), (0, 0, 0, 0))
        draw = ImageDraw.Draw(img)

        if connected:
            bg_color = (59, 185, 80, 255)
        else:
            bg_color = (88, 166, 255, 255)

        draw.ellipse([4, 4, size - 4, size - 4], fill=bg_color)

        shield_color = (255, 255, 255, 255)
        draw.polygon([
            (size // 2, 12),
            (size - 16, 20),
            (size - 16, 36),
            (size // 2, size - 12),
            (16, 36),
            (16, 20),
        ], fill=shield_color)

        inner_color = bg_color
        draw.polygon([
            (size // 2, 18),
            (size - 22, 24),
            (size - 22, 34),
            (size // 2, size - 18),
            (22, 34),
            (22, 24),
        ], fill=inner_color)

        if connected:
            check_color = (255, 255, 255, 255)
            draw.line([(22, 32), (30, 40), (42, 24)], fill=check_color, width=3)

        return img

    def _build_menu(self) -> Menu:
        
        status = self.get_status()

        if status == "connected":
            status_text = "● Подключено"
        elif status == "connecting":
            status_text = "◌ Подключение..."
        else:
            status_text = "○ Отключено"

        return Menu(
            MenuItem(status_text, None, enabled=False),
            Menu.SEPARATOR,
            MenuItem(
                "Отключиться" if status == "connected" else "Подключиться",
                self._toggle_connection
            ),
            Menu.SEPARATOR,
            MenuItem("Показать окно", self._show_window, default=True),
            MenuItem("Выход", self._quit_app),
        )

    def _toggle_connection(self, icon=None, item=None):
        status = self.get_status()
        if status == "connected":
            self.on_disconnect()
        else:
            self.on_connect()
        import threading
        def _delayed_update():
            import time
            time.sleep(0.5)
            self.update_icon()
        threading.Thread(target=_delayed_update, daemon=True).start()

    def _show_window(self, icon=None, item=None):
        self.on_show()

    def _quit_app(self, icon=None, item=None):
        self._running = False
        if self.icon:
            self.icon.stop()
        self.on_quit()

    def start(self):
        
        if not TRAY_AVAILABLE:
            return

        self._running = True

        def _run():
            connected = self.get_status() == "connected"
            image = self._create_icon_image(connected)

            self.icon = pystray.Icon(
                name="VPN Client",
                icon=image,
                title="VPN Client - Отключено",
                menu=self._build_menu()
            )

            self.icon.run()

        self._thread = threading.Thread(target=_run, daemon=True)
        self._thread.start()

    def stop(self):
        
        self._running = False
        if self.icon:
            try:
                self.icon.stop()
            except Exception:
                pass

    def update_icon(self, connected: bool = None):
        
        if not TRAY_AVAILABLE or not self.icon:
            return

        if connected is None:
            connected = self.get_status() == "connected"

        try:
            self.icon.icon = self._create_icon_image(connected)
            self.icon.menu = self._build_menu()

            if connected:
                self.icon.title = "VPN Client - Подключено"
            else:
                self.icon.title = "VPN Client - Отключено"
        except Exception:
            pass

    def notify(self, title: str, message: str):
        
        if not TRAY_AVAILABLE or not self.icon:
            return
        try:
            self.icon.notify(message, title)
        except Exception:
            pass