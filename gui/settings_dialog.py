

import customtkinter as ctk
from typing import Callable
from gui.styles import COLORS, FONTS
from core.config import AppConfig


class SettingsDialog:
    
    
    def __init__(self, parent, config: AppConfig, on_save: Callable):
        self.config = config
        self.on_save = on_save
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Настройки")
        self.dialog.geometry("500x620")
        self.dialog.configure(fg_color=COLORS["bg_primary"])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 500) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 620) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self._build_ui()
    
    def _build_ui(self):
        header = ctk.CTkFrame(self.dialog, fg_color=COLORS["bg_secondary"], height=50, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header, text="⚙️ Настройки",
            font=FONTS["subtitle"],
            text_color=COLORS["text_primary"]
        ).pack(side="left", padx=20)
        
        scroll = ctk.CTkScrollableFrame(
            self.dialog,
            fg_color="transparent",
            scrollbar_button_color=COLORS["scrollbar"],
        )
        scroll.pack(fill="both", expand=True, padx=15, pady=15)
        
        self._section_label(scroll, "Порты прокси")
        
        ports_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_secondary"], corner_radius=10)
        ports_frame.pack(fill="x", pady=(0, 15))
        
        self.socks_port = self._port_field(
            ports_frame, "SOCKS5 порт:", 
            self.config.settings["socks_port"]
        )
        
        self.http_port = self._port_field(
            ports_frame, "HTTP порт:", 
            self.config.settings["http_port"]
        )
        
        self._section_label(scroll, "DNS")

        dns_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_secondary"], corner_radius=10)
        dns_frame.pack(fill="x", pady=(0, 15))

        self.dns_server = self._text_field(
            dns_frame,
            "DNS сервер:",
            self.config.settings.get("dns_server", "8.8.8.8"),
            "Например: 8.8.8.8, 1.1.1.1, 9.9.9.9"
        )
        self._section_label(scroll, "Общие")
        
        general_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_secondary"], corner_radius=10)
        general_frame.pack(fill="x", pady=(0, 15))

        self.minimize_to_tray_var = ctk.BooleanVar(
            value=self.config.settings.get("minimize_to_tray", True)
        )
        self._switch_field(
            general_frame, "Сворачивать в трей",
            "При закрытии окна приложение продолжает работать в трее",
            self.minimize_to_tray_var
        )
        self.auto_update_var = ctk.BooleanVar(
            value=self.config.settings.get("auto_update_subs", True)
        )
        self._switch_field(
            general_frame, "Авто-обновление подписок",
            "Обновлять подписки при запуске приложения",
            self.auto_update_var
        )

        self._section_label(scroll, "Режим работы")

        mode_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_secondary"], corner_radius=10)
        mode_frame.pack(fill="x", pady=(0, 15))

        self.use_singbox_var = ctk.BooleanVar(
            value=self.config.settings.get("use_singbox", False)
        )
        self._switch_field(
            mode_frame, "Использовать sing-box",
            "Универсальный клиент (рекомендуется для TUN)",
            self.use_singbox_var
        )

        self.tun_mode_var = ctk.BooleanVar(
            value=self.config.settings.get("tun_mode", False)
        )
        self._switch_field(
            mode_frame, "TUN режим (VPN туннель)",
            "Весь трафик системы через VPN (требует sing-box и права администратора)",
            self.tun_mode_var
        )

        warning_frame = ctk.CTkFrame(mode_frame, fg_color=COLORS["bg_tertiary"], corner_radius=6)
        warning_frame.pack(fill="x", padx=15, pady=(0, 10))

        ctk.CTkLabel(
            warning_frame,
            text="⚠️ TUN режим требует запуск от имени администратора\n"
                 "и создаёт виртуальный сетевой адаптер",
            font=FONTS["tiny"],
            text_color=COLORS["warning"],
            justify="left"
        ).pack(padx=10, pady=8)

        singbox_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_secondary"], corner_radius=10)
        singbox_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            singbox_frame, text="Sing-box",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", padx=15, pady=(10, 5))

        self.singbox_path = self._path_field(
            singbox_frame, "Путь:",
            self.config.settings.get("singbox_binary", ""),
            "Путь к sing-box.exe (оставьте пустым)"
        )
        
        self.system_proxy_var = ctk.BooleanVar(
            value=self.config.settings.get("system_proxy", True)
        )
        self._switch_field(
            general_frame, "Системный прокси",
            "Автоматически устанавливать системный прокси",
            self.system_proxy_var
        )
        
        self.auto_connect_var = ctk.BooleanVar(
            value=self.config.settings.get("auto_connect", False)
        )
        self._switch_field(
            general_frame, "Автоподключение",
            "Подключаться к последнему серверу при запуске",
            self.auto_connect_var
        )

        self.auto_start_var = ctk.BooleanVar(
            value=self.config.settings.get("auto_start", False)
        )
        self._switch_field(
            general_frame, "Автозапуск с системой",
            "Запускать приложение при включении компьютера",
            self.auto_start_var
        )

        self._section_label(scroll, "Пути к программам")
        
        binary_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_secondary"], corner_radius=10)
        binary_frame.pack(fill="x", pady=(0, 15))
        
        self.xray_path = self._path_field(
            binary_frame, "Xray:",
            self.config.settings.get("xray_binary", ""),
            "Путь к xray (оставьте пустым)"
        )
        
        self.hysteria_path = self._path_field(
            binary_frame, "Hysteria:",
            self.config.settings.get("hysteria_binary", ""),
            "Путь к hysteria (оставьте пустым)"
        )

        self._section_label(scroll, "Обход VPN (Split Tunneling)")

        bypass_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_secondary"], corner_radius=10)
        bypass_frame.pack(fill="x", pady=(0, 15))

        ctk.CTkLabel(
            bypass_frame,
            text="Домены через запятую — трафик к ним идёт напрямую:",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"]
        ).pack(anchor="w", padx=15, pady=(8, 0))

        bypass_input_frame = ctk.CTkFrame(bypass_frame, fg_color="transparent")
        bypass_input_frame.pack(fill="x", padx=15, pady=(4, 10))

        self.bypass_domains = ctk.CTkEntry(
            bypass_input_frame,
            placeholder_text="youtube.com, google.com, ...",
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            height=32,
        )
        bypass_val = self.config.settings.get("bypass_domains", "")
        if bypass_val:
            self.bypass_domains.insert(0, bypass_val)
        self.bypass_domains.pack(side="left", fill="x", expand=True)

        def _paste_bypass():
            try:
                clipboard = self.dialog.clipboard_get().strip()
                if clipboard:
                    self.bypass_domains.delete(0, "end")
                    self.bypass_domains.insert(0, clipboard)
            except Exception:
                pass

        ctk.CTkButton(
            bypass_input_frame, text="📋", width=32, height=32,
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            command=_paste_bypass
        ).pack(side="right", padx=(5, 0))

        self._section_label(scroll, "Информация")
        
        info_frame = ctk.CTkFrame(scroll, fg_color=COLORS["bg_secondary"], corner_radius=10)
        info_frame.pack(fill="x", pady=(0, 15))
        
        info_content = ctk.CTkFrame(info_frame, fg_color="transparent")
        info_content.pack(fill="x", padx=15, pady=15)
        
        ctk.CTkLabel(
            info_content,
            text="VPN Client v1.2 Fix\n\n"
                 "Поддерживаемые протоколы:\n"
                 "• VLESS (TCP, WS, gRPC, H2, TLS, Reality)\n"
                 "• Hysteria2\n\n"
                 "Использовано для реализации VpnClient:\n"
                 "• Xray-core для VLESS: https://github.com/xtls/xray-core\n"
                 "• Hysteria для Hysteria2: https://github.com/apernet/hysteria\n"
                 "• Sing-box для tun: https://github.com/sagernet/sing-box\n\n"
                 "По всем вопросам в тг: @DISHACKER",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            justify="left",
            anchor="w"
        ).pack(fill="x")
        
        btn_frame = ctk.CTkFrame(self.dialog, fg_color="transparent", height=60)
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        btn_frame.pack_propagate(False)
        
        ctk.CTkButton(
            btn_frame, text="Отмена", width=100,
            font=FONTS["body"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            height=38,
            command=self.dialog.destroy
        ).pack(side="right", padx=(5, 0))
        
        ctk.CTkButton(
            btn_frame, text="💾 Сохранить", width=130,
            font=FONTS["button"],
            fg_color=COLORS["btn_primary"],
            hover_color=COLORS["btn_primary_hover"],
            height=38,
            command=self._save
        ).pack(side="right")
    
    def _section_label(self, parent, text: str):
        ctk.CTkLabel(
            parent, text=text,
            font=FONTS["heading"],
            text_color=COLORS["text_primary"]
        ).pack(anchor="w", pady=(5, 5))

    def _text_field(self, parent, label: str, value: str, placeholder: str) -> ctk.CTkEntry:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=8)

        ctk.CTkLabel(
            frame, text=label,
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
            width=120
        ).pack(side="left")

        entry = ctk.CTkEntry(
            frame,
            placeholder_text=placeholder,
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            height=32,
        )
        if value:
            entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True, padx=(10, 0))

        return entry
    
    def _port_field(self, parent, label: str, value: int) -> ctk.CTkEntry:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=8)
        
        ctk.CTkLabel(
            frame, text=label,
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
            width=120
        ).pack(side="left")
        
        entry = ctk.CTkEntry(
            frame,
            font=FONTS["mono"],
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            width=100,
            height=32,
        )
        entry.insert(0, str(value))
        entry.pack(side="left", padx=(10, 0))
        
        return entry
    
    def _switch_field(self, parent, label: str, description: str, variable: ctk.BooleanVar):
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=8)
        
        text_frame = ctk.CTkFrame(frame, fg_color="transparent")
        text_frame.pack(side="left", fill="x", expand=True)
        
        ctk.CTkLabel(
            text_frame, text=label,
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
        ).pack(anchor="w")
        
        ctk.CTkLabel(
            text_frame, text=description,
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"],
        ).pack(anchor="w")
        
        switch = ctk.CTkSwitch(
            frame,
            text="",
            variable=variable,
            onvalue=True,
            offvalue=False,
            progress_color=COLORS["accent"],
            button_color=COLORS["text_primary"],
            button_hover_color=COLORS["accent_hover"],
            fg_color=COLORS["bg_tertiary"],
        )
        switch.pack(side="right")
    
    def _path_field(self, parent, label: str, value: str, placeholder: str) -> ctk.CTkEntry:
        frame = ctk.CTkFrame(parent, fg_color="transparent")
        frame.pack(fill="x", padx=15, pady=8)
        
        ctk.CTkLabel(
            frame, text=label,
            font=FONTS["body"],
            text_color=COLORS["text_primary"],
            width=80
        ).pack(side="left")
        
        entry = ctk.CTkEntry(
            frame,
            placeholder_text=placeholder,
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            height=32,
        )
        if value:
            entry.insert(0, value)
        entry.pack(side="left", fill="x", expand=True, padx=(10, 0))
        
        def _browse():
            from tkinter import filedialog
            path = filedialog.askopenfilename(title=f"Выберите {label}")
            if path:
                entry.delete(0, "end")
                entry.insert(0, path)
        
        ctk.CTkButton(
            frame, text="📁", width=32, height=32,
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            command=_browse
        ).pack(side="right", padx=(5, 0))
        
        return entry
    
    def _save(self):
        
        try:
            socks = int(self.socks_port.get())
            http = int(self.http_port.get())
            dns_server = self.dns_server.get().strip()

            if not dns_server:
                dns_server = "8.8.8.8"
            
            if not (1 <= socks <= 65535) or not (1 <= http <= 65535):
                raise ValueError("Port out of range")
            
            self.config.settings["socks_port"] = socks
            self.config.settings["http_port"] = http
            self.config.settings["system_proxy"] = self.system_proxy_var.get()
            self.config.settings["auto_connect"] = self.auto_connect_var.get()
            self.config.settings["xray_binary"] = self.xray_path.get().strip()
            self.config.settings["hysteria_binary"] = self.hysteria_path.get().strip()
            self.config.settings["use_singbox"] = self.use_singbox_var.get()
            self.config.settings["dns_server"] = dns_server
            self.config.settings["tun_mode"] = self.tun_mode_var.get()
            self.config.settings["singbox_binary"] = self.singbox_path.get().strip()
            self.config.settings["minimize_to_tray"] = self.minimize_to_tray_var.get()
            self.config.settings["auto_update_subs"] = self.auto_update_var.get()

            self.config.settings["bypass_domains"] = self.bypass_domains.get().strip()

            auto_start_new = self.auto_start_var.get()
            auto_start_old = self.config.settings.get("auto_start", False)
            self.config.settings["auto_start"] = auto_start_new
            if auto_start_new != auto_start_old:
                from core.autostart import AutostartManager
                asm = AutostartManager()
                if auto_start_new:
                    if not asm.enable():
                        import tkinter.messagebox as messagebox
                        messagebox.showwarning("Автозапуск", "Не удалось включить автозапуск")
                else:
                    asm.disable()
            
            self.config.save_settings()
            self.on_save()
            self.dialog.destroy()
            
        except ValueError:
            import tkinter.messagebox as messagebox
            messagebox.showerror("Ошибка", "Порт должен быть числом от 1 до 65535")