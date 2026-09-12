

import customtkinter as ctk
from typing import List, Callable
from gui.styles import COLORS, FONTS
from core.config import AppConfig
from core.subscription import SubscriptionManager
from core.server import ServerConfig
from utils.parser import URIParser


class CollapsibleSubscription(ctk.CTkFrame):
    

    def __init__(self, parent, sub: dict, servers: List[ServerConfig],
                 on_delete: Callable, on_update: Callable):
        super().__init__(parent, fg_color=COLORS["bg_card"], corner_radius=8)

        self.sub = sub
        self.servers = servers
        self.on_delete = on_delete
        self.on_update = on_update
        self.is_expanded = False

        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color="transparent", cursor="hand2")
        header.pack(fill="x", padx=10, pady=(8, 4))
        header.bind("<Button-1>", lambda e: self._toggle())

        self.arrow_label = ctk.CTkLabel(
            header, text="▶",
            font=("Segoe UI", 12),
            text_color=COLORS["text_muted"],
            width=20
        )
        self.arrow_label.pack(side="left")
        self.arrow_label.bind("<Button-1>", lambda e: self._toggle())

        name_label = ctk.CTkLabel(
            header,
            text=self.sub.get('name', 'Подписка'),
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"]
        )
        name_label.pack(side="left", padx=(6, 0))
        name_label.bind("<Button-1>", lambda e: self._toggle())

        count_label = ctk.CTkLabel(
            header,
            text=f"  ({len(self.servers)})",
            font=FONTS["small"],
            text_color=COLORS["text_muted"]
        )
        count_label.pack(side="left")
        count_label.bind("<Button-1>", lambda e: self._toggle())

        ctk.CTkButton(
            header, text="✕", width=26, height=24,
            font=("Segoe UI", 11),
            fg_color="transparent",
            hover_color=COLORS["btn_danger"],
            text_color=COLORS["text_muted"],
            corner_radius=4,
            command=lambda: self.on_delete(self.sub['url'])
        ).pack(side="right", padx=2)

        ctk.CTkButton(
            header, text="🔄", width=26, height=24,
            font=("Segoe UI", 11),
            fg_color="transparent",
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_muted"],
            corner_radius=4,
            command=lambda: self.on_update(self.sub['url'], self.sub.get('name', ''))
        ).pack(side="right", padx=2)

        url_display = self.sub['url']
        if len(url_display) > 55:
            url_display = url_display[:55] + "..."

        url_label = ctk.CTkLabel(
            self,
            text=url_display,
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"],
            anchor="w"
        )
        url_label.pack(fill="x", padx=36, pady=(0, 4))
        url_label.bind("<Button-1>", lambda e: self._toggle())

        traffic = self.sub.get('traffic', {})
        from core.subscription import SubscriptionInfo
        info = SubscriptionInfo.from_dict(traffic)

        if info.has_data():
            traffic_frame = ctk.CTkFrame(self, fg_color="transparent")
            traffic_frame.pack(fill="x", padx=36, pady=(0, 4))

            if info.total > 0:
                bar = ctk.CTkProgressBar(
                    traffic_frame,
                    fg_color=COLORS["bg_tertiary"],
                    progress_color=COLORS["accent"],
                    height=4, width=120
                )
                bar.pack(side="left", padx=(0, 8))
                bar.set(info.percent_used() / 100)

                if info.percent_used() > 90:
                    bar.configure(progress_color=COLORS["error"])
                elif info.percent_used() > 70:
                    bar.configure(progress_color=COLORS["warning"])

                traffic_text = f"{info.used_str()} / {info.total_str()}"
            else:
                traffic_text = f"{info.used_str()} / ∞"

            if info.expire and info.expire != "0":
                traffic_text += f"  •  до {info.expire}"

            ctk.CTkLabel(
                traffic_frame,
                text=traffic_text,
                font=("Segoe UI", 9),
                text_color=COLORS["text_muted"]
            ).pack(side="left")

        elif info.web_page:
            link_frame = ctk.CTkFrame(self, fg_color="transparent")
            link_frame.pack(fill="x", padx=36, pady=(0, 4))

            ctk.CTkButton(
                link_frame,
                text="📊 Посмотреть трафик",
                font=("Segoe UI", 9),
                fg_color="transparent",
                hover_color=COLORS["bg_hover"],
                text_color=COLORS["accent"],
                height=22, width=180,
                anchor="w",
                command=lambda: self._open_web(info.web_page)
            ).pack(side="left")

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")

    def _toggle(self):
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.arrow_label.configure(text="▼")
            self._build_server_list()
            self.content_frame.pack(fill="x", padx=10, pady=(0, 8))
        else:
            self.arrow_label.configure(text="▶")
            self.content_frame.pack_forget()
            for w in self.content_frame.winfo_children():
                w.destroy()

    def _build_server_list(self):
        for w in self.content_frame.winfo_children():
            w.destroy()

        if not self.servers:
            ctk.CTkLabel(
                self.content_frame,
                text="  Нет серверов",
                font=FONTS["tiny"],
                text_color=COLORS["text_muted"]
            ).pack(anchor="w", pady=4)
            return

        for server in self.servers:
            row = ctk.CTkFrame(
                self.content_frame,
                fg_color=COLORS["bg_tertiary"],
                corner_radius=6,
                height=32
            )
            row.pack(fill="x", pady=1, padx=4)
            row.pack_propagate(False)

            badge_colors = {
                "vless": COLORS["badge_vless"],
                "hysteria2": COLORS["badge_hysteria2"],
            }
            badge_color = badge_colors.get(server.server_type, COLORS["accent"])

            ctk.CTkLabel(
                row,
                text=f" {server.server_type.upper()} ",
                font=("Segoe UI", 8, "bold"),
                text_color="#FFFFFF",
                fg_color=badge_color,
                corner_radius=3,
                height=16,
            ).pack(side="left", padx=(8, 6), pady=4)

            ctk.CTkLabel(
                row,
                text=server.display_name(),
                font=FONTS["tiny"],
                text_color=COLORS["text_primary"],
                anchor="w"
            ).pack(side="left", fill="x", expand=True)

            if server.latency >= 0:
                lat_color = COLORS["success"] if server.latency < 100 else \
                    COLORS["warning"] if server.latency < 300 else COLORS["error"]
                ctk.CTkLabel(
                    row,
                    text=f"{server.latency}ms",
                    font=("Segoe UI", 9),
                    text_color=lat_color,
                ).pack(side="right", padx=8)

    def _open_web(self, url: str):
        import webbrowser
        webbrowser.open(url)

class SubscriptionDialog:
    def __init__(self, parent, config: AppConfig,
                 sub_manager: SubscriptionManager,
                 on_update: Callable):
        self.config = config
        self.sub_manager = sub_manager
        self.on_update = on_update
        self.parent = parent

        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Управление подписками")
        self.dialog.geometry("680x600")
        self.dialog.configure(fg_color=COLORS["bg_primary"])
        self.dialog.transient(parent)

        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 680) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 600) // 2
        self.dialog.geometry(f"+{x}+{y}")

        self._build_ui()
        self._load_subscriptions()

        self.dialog.after(100, self._safe_grab)

    def _safe_grab(self):
        
        try:
            self.dialog.grab_set()
            self.url_entry.focus_force()
        except Exception:
            pass

    def _build_ui(self):
        header = ctk.CTkFrame(self.dialog, fg_color=COLORS["bg_secondary"],
                              height=50, corner_radius=0)
        header.pack(fill="x")
        header.pack_propagate(False)

        ctk.CTkLabel(
            header, text="📋 Управление подписками",
            font=FONTS["subtitle"],
            text_color=COLORS["text_primary"]
        ).pack(side="left", padx=20)

        add_frame = ctk.CTkFrame(self.dialog, fg_color=COLORS["bg_secondary"], corner_radius=10)
        add_frame.pack(fill="x", padx=15, pady=15)

        ctk.CTkLabel(
            add_frame, text="Добавить подписку",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"]
        ).pack(padx=15, pady=(15, 10), anchor="w")

        url_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        url_frame.pack(fill="x", padx=15, pady=(0, 5))

        ctk.CTkLabel(
            url_frame, text="URL:",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            width=50
        ).pack(side="left")

        self.url_entry = ctk.CTkEntry(
            url_frame,
            placeholder_text="https://example.com/sub",
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            height=34,
        )
        self.url_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))

        name_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        name_frame.pack(fill="x", padx=15, pady=(0, 5))

        ctk.CTkLabel(
            name_frame, text="Имя:",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            width=50
        ).pack(side="left")

        self.name_entry = ctk.CTkEntry(
            name_frame,
            placeholder_text="Авто из URL (или своё)",
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            border_color=COLORS["border"],
            text_color=COLORS["text_primary"],
            height=34,
        )
        self.name_entry.pack(side="left", fill="x", expand=True, padx=(10, 0))

        btn_frame = ctk.CTkFrame(add_frame, fg_color="transparent")
        btn_frame.pack(fill="x", padx=15, pady=(5, 15))

        self.status_label = ctk.CTkLabel(
            btn_frame, text="",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(side="left", fill="x", expand=True)

        self.add_btn = ctk.CTkButton(
            btn_frame, text="Добавить и загрузить", width=170,
            font=FONTS["body"],
            fg_color=COLORS["btn_primary"],
            hover_color=COLORS["btn_primary_hover"],
            height=36,
            command=self._add_subscription
        )
        self.add_btn.pack(side="right")

        paste_btn = ctk.CTkButton(
            btn_frame, text="📋 Вставить", width=90,
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            height=36,
            command=self._paste_url
        )
        paste_btn.pack(side="right", padx=(0, 8))

        list_frame = ctk.CTkFrame(self.dialog, fg_color=COLORS["bg_secondary"], corner_radius=10)
        list_frame.pack(fill="both", expand=True, padx=15, pady=(0, 15))

        list_header = ctk.CTkFrame(list_frame, fg_color="transparent")
        list_header.pack(fill="x", padx=15, pady=(15, 5))

        ctk.CTkLabel(
            list_header, text="Подписки",
            font=FONTS["heading"],
            text_color=COLORS["text_primary"]
        ).pack(side="left")

        ctk.CTkButton(
            list_header, text="🔄 Обновить все", width=130,
            font=FONTS["small"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            height=30,
            command=self._update_all
        ).pack(side="right")

        ctk.CTkButton(
            list_header, text="▼ Развернуть", width=110,
            font=FONTS["small"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            height=30,
            command=self._toggle_all
        ).pack(side="right", padx=(0, 8))

        self.sub_list_frame = ctk.CTkScrollableFrame(
            list_frame,
            fg_color="transparent",
            scrollbar_button_color=COLORS["scrollbar"],
        )
        self.sub_list_frame.pack(fill="both", expand=True, padx=10, pady=(5, 10))

        self._all_expanded = False
        self._sub_widgets = []

    def _paste_url(self):
        
        try:
            clipboard = self.dialog.clipboard_get()
            clipboard = clipboard.strip()
            if clipboard:
                self.url_entry.delete(0, "end")
                self.url_entry.insert(0, clipboard)
                self.url_entry.focus_force()
                self.status_label.configure(
                    text="✅ Вставлено из буфера",
                    text_color=COLORS["success"]
                )
        except Exception:
            self.status_label.configure(
                text="Буфер обмена пуст",
                text_color=COLORS["text_muted"]
            )

    def _load_subscriptions(self):
        for widget in self.sub_list_frame.winfo_children():
            widget.destroy()
        self._sub_widgets = []

        if not self.config.subscriptions:
            ctk.CTkLabel(
                self.sub_list_frame,
                text="Нет подписок\nВставьте URL выше и нажмите \"Добавить\"",
                font=FONTS["body"],
                text_color=COLORS["text_muted"],
                justify="center"
            ).pack(pady=30)
            return

        for sub in self.config.subscriptions:
            servers = [
                s for s in self.config.servers
                if s.subscription_url == sub['url']
            ]

            widget = CollapsibleSubscription(
                self.sub_list_frame,
                sub=sub,
                servers=servers,
                on_delete=self._delete_subscription,
                on_update=self._update_subscription
            )
            widget.pack(fill="x", pady=3, padx=2)
            self._sub_widgets.append(widget)

    def _toggle_all(self):
        self._all_expanded = not self._all_expanded
        for widget in self._sub_widgets:
            if isinstance(widget, CollapsibleSubscription):
                if self._all_expanded and not widget.is_expanded:
                    widget._toggle()
                elif not self._all_expanded and widget.is_expanded:
                    widget._toggle()

    def _add_subscription(self):
        url = self.url_entry.get().strip()

        if not url:
            self.status_label.configure(text="Введите URL", text_color=COLORS["warning"])
            self.url_entry.focus_force()
            return

        name = self.name_entry.get().strip()
        if not name:
            name = URIParser.extract_subscription_name(url)

        self.status_label.configure(text="⏳ Загрузка...", text_color=COLORS["info"])
        self.add_btn.configure(state="disabled")

        def _on_loaded(servers, sub_info):
            def _update():
                self.add_btn.configure(state="normal")

                if servers:
                    traffic_dict = sub_info.to_dict() if sub_info else {}
                    self.config.add_subscription(name, url, traffic_dict)
                    for s in servers:
                        s.subscription_name = name
                        s.subscription_url = url
                        self.config.add_server(s)
                    self.config.save_servers()

                    traffic_text = ""
                    if sub_info and sub_info.total > 0:
                        traffic_text = f" | {sub_info.used_str()}/{sub_info.total_str()}"

                    self.status_label.configure(
                        text=f"✅ {name}: {len(servers)} серверов{traffic_text}",
                        text_color=COLORS["success"]
                    )

                    self.name_entry.delete(0, "end")
                    self.url_entry.delete(0, "end")

                    self._load_subscriptions()
                    self.on_update()
                else:
                    self.status_label.configure(
                        text="❌ Не удалось загрузить",
                        text_color=COLORS["error"]
                    )

            self.dialog.after(0, _update)

        self.sub_manager.fetch_async(url, _on_loaded)

    def _delete_subscription(self, url: str):
        self.config.remove_subscription(url)
        self._load_subscriptions()
        self.on_update()

    def _update_subscription(self, url: str, name: str):
        self.status_label.configure(text=f"⏳ {name}...", text_color=COLORS["info"])

        def _on_loaded(servers, sub_info):
            def _update():
                self.config.servers = [
                    s for s in self.config.servers if s.subscription_url != url
                ]

                for sub in self.config.subscriptions:
                    if sub['url'] == url:
                        if sub_info:
                            sub['traffic'] = sub_info.to_dict()
                        break

                for s in servers:
                    s.subscription_name = name
                    s.subscription_url = url
                    self.config.add_server(s)
                self.config.save_servers()
                self.config.save_subscriptions()

                traffic_text = ""
                if sub_info and sub_info.total > 0:
                    traffic_text = f" | {sub_info.used_str()}/{sub_info.total_str()}"

                self.status_label.configure(
                    text=f"✅ {name}: {len(servers)} серверов{traffic_text}",
                    text_color=COLORS["success"]
                )
                self._load_subscriptions()
                self.on_update()

            self.dialog.after(0, _update)

        self.sub_manager.fetch_async(url, _on_loaded)

    def _update_all(self):
        if not self.config.subscriptions:
            self.status_label.configure(text="Нет подписок", text_color=COLORS["text_muted"])
            return

        self.status_label.configure(text="⏳ Обновление...", text_color=COLORS["info"])

        total = [0]
        remaining = [len(self.config.subscriptions)]

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

                total[0] += len(servers)
                remaining[0] -= 1

                if remaining[0] <= 0:
                    self.config.save_servers()
                    self.config.save_subscriptions()
                    self.status_label.configure(
                        text=f"✅ Всего: {total[0]} серверов",
                        text_color=COLORS["success"]
                    )
                    self._load_subscriptions()
                    self.on_update()

            self.dialog.after(0, _update)

        self.sub_manager.update_all(self.config.subscriptions, _on_loaded)