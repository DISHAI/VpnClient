

import customtkinter as ctk
import sys
from typing import Optional
from gui.main_window import MainWindow
from gui.styles import COLORS
from gui.tray import TrayIcon, TRAY_AVAILABLE


class VPNApp:
    def __init__(self, start_minimized=False):
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.root = ctk.CTk()
        self.root.title("VPN Client")
        self.root.geometry("960x680")
        self.root.minsize(800, 600)
        self.root.configure(fg_color=COLORS["bg_primary"])

        try:
            self.root.iconbitmap("icon.ico")
        except Exception:
            pass

        self.main_window = MainWindow(self.root)
        self.main_window.pack(fill="both", expand=True)

        self.tray: Optional[TrayIcon] = None
        self._hidden = False
        self._force_quit = False

        if TRAY_AVAILABLE:
            self.tray = TrayIcon(
                on_show=self._show_window,
                on_quit=self._force_quit_app,
                on_connect=self._tray_connect,
                on_disconnect=self._tray_disconnect,
                get_status=self._get_status
            )
            self.tray.start()

            self.main_window.connection_manager.add_state_callback(
                self._on_connection_state_change
            )

        self.root.protocol("WM_DELETE_WINDOW", self._on_close)

        self.root.bind("<Map>", self._on_map)

        if start_minimized and TRAY_AVAILABLE and self.tray:
            self.root.after(100, self._hide_window)

    def _on_close(self):
        
        if self._force_quit:
            self._do_quit()
            return

        if TRAY_AVAILABLE and self.tray:
            self._hide_window()
        else:
            self._do_quit()

    def _hide_window(self):
        
        self._hidden = True
        self.root.withdraw()

        if self.tray and not hasattr(self, '_notified_tray'):
            self._notified_tray = True
            self.tray.notify("VPN Client", "Приложение свёрнуто в трей")

    def _show_window(self):
        
        def _do():
            self._hidden = False
            self.root.deiconify()
            self.root.lift()
            self.root.focus_force()

            try:
                self.root.state('normal')
            except Exception:
                pass

        self.root.after(0, _do)

    def _on_map(self, event=None):
        
        self._hidden = False

    def _force_quit_app(self):
        
        self._force_quit = True
        self.root.after(0, self._do_quit)

    def _do_quit(self):
        
        try:
            self.main_window.on_close()
        except Exception:
            pass

        if self.tray:
            try:
                self.tray.stop()
            except Exception:
                pass

        try:
            self.root.destroy()
        except Exception:
            pass

        sys.exit(0)

    def _tray_connect(self):
        
        def _do():
            server = self.main_window.selected_server
            if server:
                self.main_window.connection_manager.connect(server)
            else:
                if self.tray:
                    self.tray.notify("VPN Client", "Сначала выберите сервер")
                self._show_window()

        self.root.after(0, _do)

    def _tray_disconnect(self):
        
        def _do():
            self.main_window.connection_manager.disconnect()

        self.root.after(0, _do)

    def _get_status(self) -> str:
        
        try:
            return self.main_window.connection_manager.state
        except Exception:
            return "disconnected"

    def _on_connection_state_change(self, state: str):
        
        if not self.tray:
            return

        connected = state == "connected"
        self.tray.update_icon(connected)

        if self._hidden:
            if state == "connected":
                server_name = ""
                if self.main_window.current_server_name():
                    server_name = f"\n{self.main_window.current_server_name()}"
                self.tray.notify("VPN Client", f"Подключено{server_name}")
            elif state == "error":
                self.tray.notify("VPN Client", "Ошибка подключения")
            elif state == "disconnected":
                self.tray.notify("VPN Client", "Отключено")

    def run(self):
        self.root.mainloop()