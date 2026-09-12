

import customtkinter as ctk
from typing import List, Callable, Optional, Dict
from core.server import ServerConfig
from gui.styles import COLORS, FONTS


class ServerCard(ctk.CTkFrame):
    def __init__(self, parent, server: ServerConfig,
                 on_select: Callable, on_delete: Callable,
                 on_test: Callable, is_selected: bool = False):
        super().__init__(
            parent,
            fg_color=COLORS["accent_dark"] if is_selected else COLORS["bg_card"],
            corner_radius=8,
            cursor="hand2"
        )

        self.server = server
        self.on_select = on_select
        self.on_delete = on_delete
        self.on_test = on_test
        self.is_selected = is_selected

        self._build()
        self._bind_click_recursive(self)

    def _bind_click_recursive(self, widget):
        widget.bind("<Button-1>", self._handle_click)
        widget.bind("<Enter>", self._on_enter)
        widget.bind("<Leave>", self._on_leave)
        for child in widget.winfo_children():
            if isinstance(child, ctk.CTkButton):
                continue
            self._bind_click_recursive(child)

    def _handle_click(self, event):
        self.on_select(self.server)

    def _build(self):
        top_row = ctk.CTkFrame(self, fg_color="transparent")
        top_row.pack(fill="x", padx=10, pady=(8, 2))

        badge_colors = {
            "vless": COLORS["badge_vless"],
            "hysteria2": COLORS["badge_hysteria2"],
        }
        badge_color = badge_colors.get(self.server.server_type, COLORS["accent"])

        ctk.CTkLabel(
            top_row,
            text=f" {self.server.server_type.upper()} ",
            font=FONTS["badge"],
            text_color="#FFFFFF",
            fg_color=badge_color,
            corner_radius=4,
            height=18,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkLabel(
            top_row,
            text=self.server.display_name(),
            font=FONTS["body_bold"],
            text_color=COLORS["text_primary"],
            anchor="w"
        ).pack(side="left", fill="x", expand=True)

        if self.server.is_active:
            ctk.CTkLabel(
                top_row, text="●",
                font=("Segoe UI", 12),
                text_color=COLORS["success"]
            ).pack(side="right")

        bottom_row = ctk.CTkFrame(self, fg_color="transparent")
        bottom_row.pack(fill="x", padx=10, pady=(0, 6))

        address_parts = [f"{self.server.address}:{self.server.port}"]
        if self.server.security and self.server.security != "none":
            address_parts.append(self.server.security)
        if self.server.transport and self.server.transport != "tcp":
            address_parts.append(self.server.transport)

        ctk.CTkLabel(
            bottom_row,
            text=" • ".join(address_parts),
            font=FONTS["tiny"],
            text_color=COLORS["text_muted"],
            anchor="w"
        ).pack(side="left", fill="x", expand=True)

        latency_color = COLORS["text_muted"]
        if self.server.latency >= 0:
            if self.server.latency < 100:
                latency_color = COLORS["success"]
            elif self.server.latency < 300:
                latency_color = COLORS["warning"]
            else:
                latency_color = COLORS["error"]

        ctk.CTkLabel(
            bottom_row,
            text=self.server.latency_str(),
            font=FONTS["tiny"],
            text_color=latency_color,
        ).pack(side="right", padx=(0, 4))

        ctk.CTkButton(
            bottom_row, text="📶", width=26, height=22,
            font=("Segoe UI", 10),
            fg_color="transparent",
            hover_color=COLORS["bg_hover"],
            text_color=COLORS["text_muted"],
            corner_radius=4,
            command=lambda: self.on_test(self.server)
        ).pack(side="right", padx=1)

        ctk.CTkButton(
            bottom_row, text="✕", width=26, height=22,
            font=("Segoe UI", 10),
            fg_color="transparent",
            hover_color=COLORS["btn_danger"],
            text_color=COLORS["text_muted"],
            corner_radius=4,
            command=lambda: self.on_delete(self.server)
        ).pack(side="right", padx=1)

    def _on_enter(self, event):
        if not self.is_selected:
            self.configure(fg_color=COLORS["bg_hover"])

    def _on_leave(self, event):
        if not self.is_selected:
            self.configure(fg_color=COLORS["bg_card"])

    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.configure(
            fg_color=COLORS["accent_dark"] if selected else COLORS["bg_card"]
        )


class CollapsibleGroup(ctk.CTkFrame):
    

    def __init__(self, parent, group_name: str, servers: List[ServerConfig],
                 on_select: Callable, on_delete: Callable, on_test: Callable,
                 selected_id: Optional[str] = None,
                 initially_expanded: bool = True):
        super().__init__(parent, fg_color="transparent")

        self.group_name = group_name
        self.servers = servers
        self.on_select = on_select
        self.on_delete = on_delete
        self.on_test = on_test
        self.selected_id = selected_id
        self.is_expanded = initially_expanded
        self.cards: List[ServerCard] = []

        self._build()

    def _build(self):
        header = ctk.CTkFrame(self, fg_color=COLORS["bg_tertiary"],
                              corner_radius=6, height=32, cursor="hand2")
        header.pack(fill="x", padx=2, pady=(4, 2))
        header.pack_propagate(False)

        header.bind("<Button-1>", lambda e: self.toggle())

        self.arrow_label = ctk.CTkLabel(
            header,
            text="▼" if self.is_expanded else "▶",
            font=("Segoe UI", 10),
            text_color=COLORS["text_muted"],
            width=18
        )
        self.arrow_label.pack(side="left", padx=(10, 4))
        self.arrow_label.bind("<Button-1>", lambda e: self.toggle())

        name_label = ctk.CTkLabel(
            header,
            text=self.group_name,
            font=FONTS["small"],
            text_color=COLORS["text_secondary"],
            anchor="w"
        )
        name_label.pack(side="left", fill="x", expand=True)
        name_label.bind("<Button-1>", lambda e: self.toggle())

        count_label = ctk.CTkLabel(
            header,
            text=str(len(self.servers)),
            font=FONTS["badge"],
            text_color=COLORS["text_muted"],
            fg_color=COLORS["bg_hover"],
            corner_radius=8,
            width=28, height=18,
        )
        count_label.pack(side="right", padx=10)
        count_label.bind("<Button-1>", lambda e: self.toggle())

        self.content_frame = ctk.CTkFrame(self, fg_color="transparent")

        if self.is_expanded:
            self.content_frame.pack(fill="x", padx=0, pady=0)
            self._build_cards()

    def _build_cards(self):
        for w in self.content_frame.winfo_children():
            w.destroy()
        self.cards.clear()

        for server in self.servers:
            card = ServerCard(
                self.content_frame, server,
                on_select=self.on_select,
                on_delete=self.on_delete,
                on_test=self.on_test,
                is_selected=(server.id == self.selected_id)
            )
            card.pack(fill="x", padx=6, pady=1)
            self.cards.append(card)

    def toggle(self):
        self.is_expanded = not self.is_expanded

        if self.is_expanded:
            self.arrow_label.configure(text="▼")
            self._build_cards()
            self.content_frame.pack(fill="x", padx=0, pady=0)
        else:
            self.arrow_label.configure(text="▶")
            self.content_frame.pack_forget()
            for w in self.content_frame.winfo_children():
                w.destroy()
            self.cards.clear()

    def update_selection(self, selected_id: Optional[str]):
        self.selected_id = selected_id
        for card in self.cards:
            card.set_selected(card.server.id == selected_id)


class ServerListPanel(ctk.CTkScrollableFrame):
    def __init__(self, parent, on_select: Callable, on_delete: Callable,
                 on_test: Callable):
        super().__init__(
            parent,
            fg_color="transparent",
            scrollbar_button_color=COLORS["scrollbar"],
            scrollbar_button_hover_color=COLORS["scrollbar_hover"],
        )

        self.on_select = on_select
        self.on_delete = on_delete
        self.on_test = on_test
        self.selected_id: Optional[str] = None
        self.groups: List[CollapsibleGroup] = []
        self._expanded_state: Dict[str, bool] = {}

    def update_servers(self, servers: List[ServerConfig]):
        for group in self.groups:
            self._expanded_state[group.group_name] = group.is_expanded

        for widget in self.winfo_children():
            widget.destroy()
        self.groups.clear()

        if not servers:
            ctk.CTkLabel(
                self,
                text="\n\n  Нет серверов\n\n  Добавьте сервер или подписку",
                font=FONTS["body"],
                text_color=COLORS["text_muted"],
                justify="left",
                anchor="w"
            ).pack(pady=40, padx=20)
            return

        grouped: Dict[str, List[ServerConfig]] = {}
        ungrouped: List[ServerConfig] = []

        for server in servers:
            if server.subscription_name:
                key = server.subscription_name
            elif server.subscription_url:
                key = server.subscription_url
            else:
                ungrouped.append(server)
                continue

            if key not in grouped:
                grouped[key] = []
            grouped[key].append(server)

        if not grouped and ungrouped:
            self._show_flat_list(ungrouped)
            return

        if ungrouped:
            group_name = "Добавленные вручную"
            expanded = self._expanded_state.get(group_name, True)
            group = CollapsibleGroup(
                self,
                group_name=group_name,
                servers=ungrouped,
                on_select=self._handle_select,
                on_delete=self.on_delete,
                on_test=self.on_test,
                selected_id=self.selected_id,
                initially_expanded=expanded,
            )
            group.pack(fill="x", padx=2, pady=1)
            self.groups.append(group)

        for group_name, group_servers in grouped.items():
            expanded = self._expanded_state.get(group_name, True)
            group = CollapsibleGroup(
                self,
                group_name=group_name,
                servers=group_servers,
                on_select=self._handle_select,
                on_delete=self.on_delete,
                on_test=self.on_test,
                selected_id=self.selected_id,
                initially_expanded=expanded,
            )
            group.pack(fill="x", padx=2, pady=1)
            self.groups.append(group)

    def _show_flat_list(self, servers: List[ServerConfig]):
        
        for server in servers:
            card = ServerCard(
                self, server,
                on_select=self._handle_select,
                on_delete=self.on_delete,
                on_test=self.on_test,
                is_selected=(server.id == self.selected_id)
            )
            card.pack(fill="x", padx=4, pady=2)

    def _handle_select(self, server: ServerConfig):
        self.selected_id = server.id
        for group in self.groups:
            group.update_selection(server.id)
        for widget in self.winfo_children():
            if isinstance(widget, ServerCard):
                widget.set_selected(widget.server.id == server.id)
        self.on_select(server)