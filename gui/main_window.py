

import customtkinter as ctk
import os
import threading
import time
from typing import Optional
from gui.styles import COLORS, FONTS
from gui.server_list import ServerListPanel
from gui.subscription_manager import SubscriptionDialog
from gui.settings_dialog import SettingsDialog
from core.config import AppConfig
from core.connection_manager import ConnectionManager, ConnectionState
from core.subscription import SubscriptionManager, SubscriptionInfo
from utils.logger import get_logger


class MainWindow(ctk.CTkFrame):
    def __init__(self, parent):
        super().__init__(parent, fg_color=COLORS["bg_primary"])

        self.config = AppConfig()
        self.connection_manager = ConnectionManager(self.config)
        self.subscription_manager = SubscriptionManager()
        self.logger = get_logger()

        self.selected_server = None
        self._timer_running = False

        self.connection_manager.add_state_callback(self._on_state_change)
        self.logger.add_callback(self._on_log_entry)

        self._build_ui()
        self._load_initial_data()

    def _build_ui(self):
        self.top_bar = ctk.CTkFrame(
            self, fg_color=COLORS["bg_secondary"], height=60, corner_radius=0
        )
        self.top_bar.pack(fill="x")
        self.top_bar.pack_propagate(False)

        logo_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        logo_frame.pack(side="left", padx=20, pady=10)

        ctk.CTkLabel(
            logo_frame, text="🛡️ VPN Client",
            font=FONTS["subtitle"],
            text_color=COLORS["text_primary"]
        ).pack(side="left")

        ctk.CTkLabel(
            logo_frame, text="  Created by DISHACKER",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"]
        ).pack(side="left", pady=(4, 0))

        btn_frame = ctk.CTkFrame(self.top_bar, fg_color="transparent")
        btn_frame.pack(side="right", padx=20, pady=10)

        ctk.CTkButton(
            btn_frame, text="⚙️ Настройки", width=120,
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            command=self._open_settings
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, text="📋 Подписки", width=120,
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            command=self._open_subscriptions
        ).pack(side="right", padx=5)

        ctk.CTkButton(
            btn_frame, text="➕ Добавить", width=120,
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            command=self._add_server_dialog
        ).pack(side="right", padx=5)

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True)

        self.left_panel = ctk.CTkFrame(
            content, fg_color=COLORS["bg_secondary"],
            width=380, corner_radius=0
        )
        self.left_panel.pack(side="left", fill="y")
        self.left_panel.pack_propagate(False)

        list_header = ctk.CTkFrame(self.left_panel, fg_color="transparent", height=50)
        list_header.pack(fill="x", padx=15, pady=(10, 5))
        list_header.pack_propagate(False)

        ctk.CTkLabel(
            list_header, text="Серверы",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"]
        ).pack(side="left")

        self.server_count_label = ctk.CTkLabel(
            list_header, text="0",
            font=FONTS["badge"],
            text_color=COLORS["text_muted"]
        )
        self.server_count_label.pack(side="left", padx=(8, 0))

        self.btn_ping_all = ctk.CTkButton(
            list_header, text="📶 Все", width=75, height=28,
            font=FONTS["tiny"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            command=self._ping_all_servers
        )
        self.btn_ping_all.pack(side="right", padx=(0, 4))

        self.search_var = ctk.StringVar()
        self.search_var.trace_add("write", self._on_search)

        ctk.CTkEntry(
            self.left_panel,
            placeholder_text="🔍 Поиск серверов...",
            textvariable=self.search_var,
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            height=35,
        ).pack(fill="x", padx=15, pady=(0, 10))

        filter_frame = ctk.CTkFrame(self.left_panel, fg_color="transparent", height=35)
        filter_frame.pack(fill="x", padx=15, pady=(0, 5))
        filter_frame.pack_propagate(False)

        self.filter_var = ctk.StringVar(value="all")
        self._filter_buttons = {}

        filters = [("Все", "all"), ("VLESS", "vless"), ("Hysteria2", "hysteria2")]
        for text, value in filters:
            btn = ctk.CTkButton(
                filter_frame, text=text, width=80, height=28,
                font=FONTS["tiny"],
                fg_color=COLORS["accent"] if value == "all" else COLORS["bg_tertiary"],
                hover_color=COLORS["accent_hover"],
                command=lambda v=value: self._set_filter(v)
            )
            btn.pack(side="left", padx=2)
            self._filter_buttons[value] = btn

        self.server_list = ServerListPanel(
            self.left_panel,
            on_select=self._on_server_select,
            on_delete=self._on_server_delete,
            on_test=self._on_server_test
        )
        self.server_list.pack(fill="both", expand=True, padx=5, pady=5)

        self.right_panel = ctk.CTkFrame(content, fg_color=COLORS["bg_primary"], corner_radius=0)
        self.right_panel.pack(side="right", fill="both", expand=True)

        self._build_connection_panel()
        self._build_log_panel()

    def _update_traffic_display(self):
        
        if not self.selected_server:
            self.traffic_frame.pack_forget()
            return

        sub_url = self.selected_server.subscription_url
        if not sub_url:
            self.traffic_frame.pack_forget()
            return

        traffic = None
        for sub in self.config.subscriptions:
            if sub['url'] == sub_url:
                traffic = sub.get('traffic', {})
                break

        if not traffic:
            self.traffic_frame.pack_forget()
            return

        from core.subscription import SubscriptionInfo
        info = SubscriptionInfo.from_dict(traffic)

        if not info.has_data():
            self.traffic_frame.pack_forget()
            return

        self.traffic_frame.pack(fill="x", padx=30, pady=(0, 15))

        if info.total > 0:
            percent = info.percent_used() / 100
            percent_text = f"{info.percent_used():.0f}%"

            if percent > 0.9:
                bar_color = COLORS["error"]
                percent_color = COLORS["error"]
            elif percent > 0.7:
                bar_color = COLORS["warning"]
                percent_color = COLORS["warning"]
            else:
                bar_color = COLORS["accent"]
                percent_color = COLORS["accent"]

            self.traffic_bar_fill.configure(fg_color=bar_color)
            self.traffic_bar_fill.place(relx=0, rely=0, relheight=1, relwidth=max(0.01, percent))
            self.traffic_percent_label.configure(text=percent_text, text_color=percent_color)
        else:
            self.traffic_bar_fill.configure(fg_color=COLORS["success"])
            self.traffic_bar_fill.place(relx=0, rely=0, relheight=1, relwidth=0.05)
            self.traffic_percent_label.configure(text="∞", text_color=COLORS["success"])

        up_str = info.format_bytes(info.upload)
        down_str = info.format_bytes(info.download)
        self.traffic_used_label.configure(text=f"↑ {up_str}  ↓ {down_str}")

        if info.total > 0:
            self.traffic_total_label.configure(text=f"Осталось: {info.remaining_str()}")
        else:
            self.traffic_total_label.configure(text="Безлимит")

        extra_parts = []
        if info.total > 0:
            extra_parts.append(f"Использовано: {info.used_str()} из {info.total_str()}")
        else:
            extra_parts.append(f"Использовано: {info.used_str()}")

        if info.expire and info.expire != "0":
            extra_parts.append(f"Действует до: {info.expire}")

        self.traffic_extra_label.configure(text="  •  ".join(extra_parts))
        
    def _build_connection_panel(self):
        conn_frame = ctk.CTkFrame(
            self.right_panel, fg_color=COLORS["bg_secondary"],
            corner_radius=12
        )
        conn_frame.pack(fill="x", padx=20, pady=20)

        status_frame = ctk.CTkFrame(conn_frame, fg_color="transparent")
        status_frame.pack(fill="x", padx=30, pady=(25, 10))

        self.status_indicator = ctk.CTkLabel(
            status_frame, text="●",
            font=("Segoe UI", 24),
            text_color=COLORS["text_muted"]
        )
        self.status_indicator.pack(side="left")

        self.status_label = ctk.CTkLabel(
            status_frame, text="Отключено",
            font=FONTS["subtitle"],
            text_color=COLORS["text_primary"]
        )
        self.status_label.pack(side="left", padx=(10, 0))

        self.timer_label = ctk.CTkLabel(
            status_frame, text="",
            font=FONTS["mono"],
            text_color=COLORS["text_secondary"]
        )
        self.timer_label.pack(side="right")

        server_info = ctk.CTkFrame(conn_frame, fg_color=COLORS["bg_tertiary"], corner_radius=8)
        server_info.pack(fill="x", padx=30, pady=(5, 15))

        self.server_name_label = ctk.CTkLabel(
            server_info, text="Выберите сервер",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        self.server_name_label.pack(padx=15, pady=(10, 2), anchor="w")

        self.server_detail_label = ctk.CTkLabel(
            server_info, text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        self.server_detail_label.pack(padx=15, pady=(0, 10), anchor="w")

        self.traffic_frame = ctk.CTkFrame(conn_frame, fg_color=COLORS["bg_tertiary"], corner_radius=8)

        traffic_header = ctk.CTkFrame(self.traffic_frame, fg_color="transparent")
        traffic_header.pack(fill="x", padx=15, pady=(10, 0))

        ctk.CTkLabel(
            traffic_header, text="📊",
            font=("Segoe UI", 14),
            text_color=COLORS["text_secondary"]
        ).pack(side="left")

        ctk.CTkLabel(
            traffic_header, text="Трафик",
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        ).pack(side="left", padx=(6, 0))

        self.traffic_percent_label = ctk.CTkLabel(
            traffic_header, text="",
            font=FONTS["body_bold"],
            text_color=COLORS["accent"]
        )
        self.traffic_percent_label.pack(side="right")

        bar_bg = ctk.CTkFrame(
            self.traffic_frame, fg_color=COLORS["bg_primary"],
            corner_radius=6, height=14
        )
        bar_bg.pack(fill="x", padx=15, pady=(8, 0))
        bar_bg.pack_propagate(False)

        self.traffic_bar_fill = ctk.CTkFrame(
            bar_bg, fg_color=COLORS["accent"],
            corner_radius=6, height=14
        )
        self.traffic_bar_fill.place(relx=0, rely=0, relheight=1, relwidth=0)

        traffic_details = ctk.CTkFrame(self.traffic_frame, fg_color="transparent")
        traffic_details.pack(fill="x", padx=15, pady=(6, 0))

        self.traffic_used_label = ctk.CTkLabel(
            traffic_details, text="",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"]
        )
        self.traffic_used_label.pack(side="left")

        self.traffic_total_label = ctk.CTkLabel(
            traffic_details, text="",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"]
        )
        self.traffic_total_label.pack(side="right")

        self.traffic_extra_label = ctk.CTkLabel(
            self.traffic_frame, text="",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"]
        )
        self.traffic_extra_label.pack(padx=15, pady=(2, 10))

        btn_row = ctk.CTkFrame(conn_frame, fg_color="transparent")
        btn_row.pack(fill="x", padx=30, pady=(5, 10))

        self.btn_connect = ctk.CTkButton(
            btn_row,
            text="⚡ Подключиться",
            font=FONTS["button"],
            fg_color=COLORS["btn_primary"],
            hover_color=COLORS["btn_primary_hover"],
            height=48,
            corner_radius=10,
            command=self._toggle_connection
        )
        self.btn_connect.pack(side="left", fill="x", expand=True)

        self.btn_diagnose = ctk.CTkButton(
            btn_row,
            text="🔍",
            font=FONTS["body"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            width=48, height=48,
            corner_radius=10,
            command=self._open_diagnostics
        )
        self.btn_diagnose.pack(side="right", padx=(10, 0))

        self.proxy_info_label = ctk.CTkLabel(
            conn_frame,
            text=f"SOCKS5: 127.0.0.1:{self.config.settings['socks_port']}  |  "
                 f"HTTP: 127.0.0.1:{self.config.settings['http_port']}",
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"]
        )
        self.proxy_info_label.pack(pady=(0, 15))

    def _build_log_panel(self):
        log_frame = ctk.CTkFrame(
            self.right_panel, fg_color=COLORS["bg_secondary"], corner_radius=12
        )
        log_frame.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        log_header = ctk.CTkFrame(log_frame, fg_color="transparent")
        log_header.pack(fill="x", padx=15, pady=(10, 5))

        ctk.CTkLabel(
            log_header, text="📝 Логи",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"]
        ).pack(side="left")

        ctk.CTkButton(
            log_header, text="🗑 Очистить", width=80,
            font=FONTS["tiny"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            height=28,
            command=self._clear_all_logs
        ).pack(side="right")

        ctk.CTkButton(
            log_header, text="📁 Папка", width=80,
            font=FONTS["tiny"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            height=28,
            command=self._open_logs_folder
        ).pack(side="right", padx=(0, 5))

        ctk.CTkButton(
            log_header, text="📋 Копировать", width=100,
            font=FONTS["tiny"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            height=28,
            command=self._copy_logs
        ).pack(side="right", padx=(0, 5))

        self.log_text = ctk.CTkTextbox(
            log_frame,
            font=FONTS["mono_small"],
            fg_color=COLORS["bg_primary"],
            text_color=COLORS["text_secondary"],
            corner_radius=8,
            wrap="word",
            state="disabled"
        )
        self.log_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))
    
    def _load_initial_data(self):
        if self.config.settings.get("system_proxy", True):
            try:
                from core.tun_manager import SystemProxyManager
                SystemProxyManager().unset_proxy()
            except Exception:
                pass

        self._refresh_server_list()
        self.logger.info("VPN Client запущен")
        if self.config.settings.get("auto_update_subs", True):
            self.after(1000, self._auto_update_subscriptions)
        elif self.config.settings.get("auto_connect", False):
            self.after(1000, self._auto_connect)

    def _auto_connect(self):
        
        last_key = self.config.settings.get("selected_server_id", "")
        if last_key:
            parts = last_key.split(":")
            if len(parts) == 3:
                addr, port, stype = parts
                for s in self.config.servers:
                    if s.address == addr and str(s.port) == port and s.server_type == stype:
                        self.logger.info(f"Автоподключение к {s.display_name()}...")
                        self._on_server_select(s)
                        self.connection_manager.connect(s)
                        return

        servers = self.config.servers
        if servers:
            self.logger.info(f"Автоподключение к {servers[0].display_name()}...")
            self._on_server_select(servers[0])
            self.connection_manager.connect(servers[0])
        else:
            self.logger.info("Автоподключение: нет серверов")

    def _auto_update_subscriptions(self):
        
        if not self.config.subscriptions:
            return
        
        self.logger.info("Авто-обновление подписок...")
        
        total_servers = [0]
        remaining = [len(self.config.subscriptions)]
        
        if remaining[0] == 0:
            return
        
        def _on_loaded(url: str, servers, sub_info):
            def _update():
                self.config.servers = [
                    s for s in self.config.servers if s.subscription_url != url
                ]
                
                sub_name = ""
                for sub in self.config.subscriptions:
                    if sub['url'] == url:
                        sub_name = sub.get('name', '')
                        if sub_info:
                            sub['traffic'] = sub_info.to_dict()
                        break
                
                for s in servers:
                    s.subscription_name = sub_name
                    s.subscription_url = url
                    self.config.add_server(s)
                
                total_servers[0] += len(servers)
                remaining[0] -= 1
                
                if remaining[0] <= 0:
                    self.config.save_servers()
                    self.config.save_subscriptions()
                    self._refresh_server_list(
                        filter_type=self.filter_var.get(),
                        search=self.search_var.get()
                    )
                    self.logger.info(f"Подписки обновлены: {total_servers[0]} серверов")

                    if self.selected_server:
                        self._update_traffic_display()

                    if self.config.settings.get("auto_connect", False):
                        self.after(500, self._auto_connect)
            
            self.after(0, _update)
        
        self.subscription_manager.update_all(
            self.config.subscriptions, _on_loaded
        )

    def _refresh_server_list(self, filter_type: str = "all", search: str = ""):
        servers = self.config.servers

        if filter_type != "all":
            servers = [s for s in servers if s.server_type == filter_type]

        if search:
            sl = search.lower()
            servers = [
                s for s in servers
                if sl in s.display_name().lower()
                or sl in s.address.lower()
                or sl in s.server_type.lower()
            ]

        self.server_list.update_servers(servers)
        self.server_count_label.configure(text=str(len(servers)))

    def _on_search(self, *args):
        self._refresh_server_list(
            filter_type=self.filter_var.get(),
            search=self.search_var.get()
        )

    def _set_filter(self, filter_type: str):
        self.filter_var.set(filter_type)
        for value, btn in self._filter_buttons.items():
            btn.configure(
                fg_color=COLORS["accent"] if value == filter_type else COLORS["bg_tertiary"]
            )
        self._refresh_server_list(
            filter_type=filter_type,
            search=self.search_var.get()
        )

    def _on_server_select(self, server):
        self.selected_server = server
        self.config.settings["selected_server_id"] = f"{server.address}:{server.port}:{server.server_type}"
        self.config.save_settings()
        self.server_name_label.configure(text=server.display_name())
        detail = f"{server.server_type.upper()} • {server.address}:{server.port}"
        if server.latency >= 0:
            detail += f" • {server.latency}ms"
        self.server_detail_label.configure(text=detail)
        self._update_traffic_display()

    def _on_server_delete(self, server):
        self.config.remove_server(server.id)
        if self.selected_server and self.selected_server.id == server.id:
            self.selected_server = None
            self.server_name_label.configure(text="Выберите сервер")
            self.server_detail_label.configure(text="")
        self._refresh_server_list(
            filter_type=self.filter_var.get(),
            search=self.search_var.get()
        )

    def _on_server_test(self, server):
        def _on_result(latency):
            self.after(0, lambda: self._refresh_server_list(
                filter_type=self.filter_var.get(),
                search=self.search_var.get()
            ))
            if self.selected_server and self.selected_server.id == server.id:
                self.after(0, lambda: self._on_server_select(server))

        self.connection_manager.test_latency(server, _on_result)

    def _ping_all_servers(self):
        servers = list(self.config.servers)
        if not servers:
            self.logger.warning("Нет серверов для пинга")
            return

        self.logger.info(f"Пинг {len(servers)} серверов...")
        self.btn_ping_all.configure(state="disabled", text="⏳ ...")

        completed = [0]
        total = len(servers)

        def _on_one_result(latency):
            completed[0] += 1
            if completed[0] % 3 == 0 or completed[0] == total:
                self.after(0, lambda: self._refresh_server_list(
                    filter_type=self.filter_var.get(),
                    search=self.search_var.get()
                ))

        def _ping_worker():
            import time as _time
            for server in servers:
                self.connection_manager.test_latency(server, _on_one_result)
                _time.sleep(0.15)

            _time.sleep(2)

            def _finish():
                self.config.save_servers()
                self._refresh_server_list(
                    filter_type=self.filter_var.get(),
                    search=self.search_var.get()
                )
                self.logger.info("Пинг всех серверов завершён")
                self.btn_ping_all.configure(state="normal", text="📶 Все")
                if self.selected_server:
                    self._on_server_select(self.selected_server)

            self.after(0, _finish)

        threading.Thread(target=_ping_worker, daemon=True).start()

    def _toggle_connection(self):
        if self.connection_manager.is_connected() or \
                self.connection_manager.state == ConnectionState.CONNECTING:
            self.connection_manager.disconnect()
        else:
            if not self.selected_server:
                self.logger.warning("Выберите сервер для подключения")
                return
            self.connection_manager.connect(self.selected_server)

    def _on_state_change(self, state: str):
        def _update():
            if state == ConnectionState.CONNECTED:
                use_tun = self.config.settings.get("tun_mode", False)
                mode_text = " [TUN]" if use_tun else ""
                self.status_indicator.configure(text_color=COLORS["success"])
                self.status_label.configure(text="Подключено")
                self.btn_connect.configure(
                    text="⏹ Отключиться",
                    fg_color=COLORS["btn_danger"],
                    hover_color=COLORS["btn_danger_hover"]
                )
                self._start_timer()

            elif state == ConnectionState.CONNECTING:
                self.status_indicator.configure(text_color=COLORS["warning"])
                self.status_label.configure(text="Подключение...")
                self.btn_connect.configure(
                    text="⏳ Подключение...",
                    fg_color=COLORS["warning"],
                    hover_color=COLORS["warning"]
                )

            elif state == ConnectionState.DISCONNECTING:
                self.status_indicator.configure(text_color=COLORS["warning"])
                self.status_label.configure(text="Отключение...")

            elif state == ConnectionState.ERROR:
                self.status_indicator.configure(text_color=COLORS["error"])
                self.status_label.configure(text="Ошибка подключения")
                self.btn_connect.configure(
                    text="⚡ Подключиться",
                    fg_color=COLORS["btn_primary"],
                    hover_color=COLORS["btn_primary_hover"]
                )
                self._stop_timer()

            else:
                self.status_indicator.configure(text_color=COLORS["text_muted"])
                self.status_label.configure(text="Отключено")
                self.btn_connect.configure(
                    text="⚡ Подключиться",
                    fg_color=COLORS["btn_primary"],
                    hover_color=COLORS["btn_primary_hover"]
                )
                self._stop_timer()
                self.timer_label.configure(text="")

        self.after(0, _update)

    def _start_timer(self):
        self._timer_running = True
        self._timer_event = threading.Event()

        def _update_timer():
            while self._timer_running and not self._timer_event.is_set():
                duration = self.connection_manager.get_connection_duration()
                try:
                    self.after(0, lambda d=duration: self.timer_label.configure(text=d))
                except Exception:
                    break
                self._timer_event.wait(1)

        threading.Thread(target=_update_timer, daemon=True).start()

    def _stop_timer(self):
        self._timer_running = False
        if hasattr(self, '_timer_event'):
            self._timer_event.set()

    def _on_log_entry(self, entry: dict):
        def _append():
            try:
                self.log_text.configure(state="normal")
                text = f"[{entry['time']}] [{entry['level']}] {entry['message']}\n"
                self.log_text.insert("end", text)
                self.log_text.see("end")
                self.log_text.configure(state="disabled")
            except Exception:
                pass

        try:
            self.after(0, _append)
        except Exception:
            pass

    def _clear_logs(self):
        self.log_text.configure(state="normal")
        self.log_text.delete("1.0", "end")
        self.log_text.configure(state="disabled")

    def _clear_all_logs(self):
        self.logger.clear_all_logs()
        self._clear_logs()
        self.logger.info("Все лог-файлы очищены")

    def _open_logs_folder(self):
        import subprocess
        log_dir = self.logger.get_log_dir()
        os.startfile(log_dir)

    def _copy_logs(self):
        self.clipboard_clear()
        self.clipboard_append(self.log_text.get("1.0", "end"))
        self.logger.info("Логи скопированы в буфер обмена")

    def _add_server_dialog(self):
        dialog = ctk.CTkToplevel(self)
        dialog.title("Добавить сервер")
        dialog.geometry("550x350")
        dialog.configure(fg_color=COLORS["bg_primary"])
        dialog.transient(self.winfo_toplevel())
        dialog.grab_set()

        dialog.update_idletasks()
        x = self.winfo_toplevel().winfo_x() + (self.winfo_toplevel().winfo_width() - 550) // 2
        y = self.winfo_toplevel().winfo_y() + (self.winfo_toplevel().winfo_height() - 350) // 2
        dialog.geometry(f"+{x}+{y}")

        frame = ctk.CTkFrame(dialog, fg_color=COLORS["bg_secondary"], corner_radius=12)
        frame.pack(fill="both", expand=True, padx=20, pady=20)

        ctk.CTkLabel(
            frame, text="Добавить сервер",
            font=FONTS["subtitle"],
            text_color=COLORS["text_primary"]
        ).pack(padx=20, pady=(20, 5))

        ctk.CTkLabel(
            frame, text="Вставьте ссылку vless://, hysteria2://, hy2://",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        ).pack(padx=20, pady=(0, 15))

        uri_text = ctk.CTkTextbox(
            frame,
            font=FONTS["mono_small"],
            fg_color=COLORS["bg_primary"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            height=120,
            wrap="word"
        )
        uri_text.pack(fill="x", padx=20, pady=(0, 10))

        status_label = ctk.CTkLabel(
            frame, text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        status_label.pack(padx=20)

        def _add():
            from utils.parser import URIParser
            text = uri_text.get("1.0", "end").strip()
            if not text:
                status_label.configure(text="Вставьте ссылку", text_color=COLORS["warning"])
                return

            added = 0
            for line in text.strip().split("\n"):
                line = line.strip()
                if not line:
                    continue
                server = URIParser.parse(line)
                if server:
                    self.config.add_server(server)
                    added += 1

            if added > 0:
                self.config.save_servers()
                self._refresh_server_list(
                    filter_type=self.filter_var.get(),
                    search=self.search_var.get()
                )
                self.logger.info(f"Добавлено {added} серверов")
                status_label.configure(
                    text=f"✅ Добавлено {added} серверов",
                    text_color=COLORS["success"]
                )
                dialog.after(1200, dialog.destroy)
            else:
                status_label.configure(
                    text="❌ Не удалось распознать ссылки",
                    text_color=COLORS["error"]
                )

        btn_frame = ctk.CTkFrame(frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=20, pady=(5, 20))

        ctk.CTkButton(
            btn_frame, text="Отмена", width=100,
            font=FONTS["body"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            command=dialog.destroy
        ).pack(side="right", padx=(5, 0))

        ctk.CTkButton(
            btn_frame, text="Добавить", width=120,
            font=FONTS["button"],
            fg_color=COLORS["btn_primary"],
            hover_color=COLORS["btn_primary_hover"],
            command=_add
        ).pack(side="right")

    def _open_subscriptions(self):
        SubscriptionDialog(
            self.winfo_toplevel(),
            self.config,
            self.subscription_manager,
            on_update=lambda: self._refresh_server_list(
                filter_type=self.filter_var.get(),
                search=self.search_var.get()
            )
        )

    def _open_settings(self):
        SettingsDialog(
            self.winfo_toplevel(),
            self.config,
            on_save=self._on_settings_saved
        )

    def _on_settings_saved(self):
        self.proxy_info_label.configure(
            text=f"SOCKS5: 127.0.0.1:{self.config.settings['socks_port']}  |  "
                 f"HTTP: 127.0.0.1:{self.config.settings['http_port']}"
        )
        self.logger.info(f"DNS сервер: {self.config.settings.get('dns_server', '8.8.8.8')}")

    def _open_diagnostics(self):
        if not self.selected_server:
            self.logger.warning("Выберите сервер для диагностики")
            return
        from gui.diagnostics_dialog import DiagnosticsDialog
        DiagnosticsDialog(
            self.winfo_toplevel(),
            self.selected_server,
            self.config
        )

    def current_server_name(self) -> str:
        
        if self.selected_server:
            return self.selected_server.display_name()
        return ""
        
    def on_close(self):
        self._timer_running = False
        if self.connection_manager.is_connected():
            self.connection_manager.disconnect()
        self.config.save_servers()
        self.config.save_settings()