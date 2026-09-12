

import customtkinter as ctk
from gui.styles import COLORS, FONTS
from core.diagnostics import DiagnosticsManager


class DiagnosticsDialog:
    
    
    def __init__(self, parent, server, config):
        self.server = server
        self.config = config
        self.diagnostics = DiagnosticsManager()
        
        self.dialog = ctk.CTkToplevel(parent)
        self.dialog.title("Диагностика подключения")
        self.dialog.geometry("720x580")
        self.dialog.configure(fg_color=COLORS["bg_primary"])
        self.dialog.transient(parent)
        self.dialog.grab_set()
        
        self.dialog.update_idletasks()
        x = parent.winfo_x() + (parent.winfo_width() - 720) // 2
        y = parent.winfo_y() + (parent.winfo_height() - 580) // 2
        self.dialog.geometry(f"+{x}+{y}")
        
        self._build_ui()
        self._start_diagnostics()
    
    def _build_ui(self):
        header = ctk.CTkFrame(
            self.dialog, fg_color=COLORS["bg_secondary"], 
            height=55, corner_radius=0
        )
        header.pack(fill="x")
        header.pack_propagate(False)
        
        ctk.CTkLabel(
            header,
            text=f"🔍 Диагностика: {self.server.display_name()}",
            font=FONTS["subtitle"],
            text_color=COLORS["text_primary"]
        ).pack(side="left", padx=20, pady=15)
        
        self.progress = ctk.CTkProgressBar(
            self.dialog,
            fg_color=COLORS["bg_tertiary"],
            progress_color=COLORS["accent"],
            mode="indeterminate"
        )
        self.progress.pack(fill="x", padx=0, pady=0)
        self.progress.start()
        
        self.status_label = ctk.CTkLabel(
            self.dialog,
            text="⏳ Запуск диагностики...",
            font=FONTS["small"],
            text_color=COLORS["text_secondary"]
        )
        self.status_label.pack(pady=(10, 5))
        
        self.result_text = ctk.CTkTextbox(
            self.dialog,
            font=FONTS["mono_small"],
            fg_color=COLORS["bg_secondary"],
            text_color=COLORS["text_primary"],
            corner_radius=8,
            wrap="word",
            state="disabled"
        )
        self.result_text.pack(fill="both", expand=True, padx=15, pady=(5, 15))
        
        btn_frame = ctk.CTkFrame(self.dialog, fg_color="transparent", height=50)
        btn_frame.pack(fill="x", padx=15, pady=(0, 15))
        btn_frame.pack_propagate(False)
        
        ctk.CTkButton(
            btn_frame, text="📋 Скопировать", width=140,
            font=FONTS["body"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            height=36,
            command=self._copy_results
        ).pack(side="left")
        
        self.btn_retry = ctk.CTkButton(
            btn_frame, text="🔄 Повторить", width=120,
            font=FONTS["body"],
            fg_color=COLORS["accent"],
            hover_color=COLORS["accent_hover"],
            height=36,
            command=self._start_diagnostics
        )
        self.btn_retry.pack(side="left", padx=(10, 0))
        
        ctk.CTkButton(
            btn_frame, text="Закрыть", width=100,
            font=FONTS["body"],
            fg_color=COLORS["bg_tertiary"],
            hover_color=COLORS["bg_hover"],
            height=36,
            command=self.dialog.destroy
        ).pack(side="right")
    
    def _append_text(self, text: str, color: str = None):
        
        def _do():
            self.result_text.configure(state="normal")
            self.result_text.insert("end", text + "\n")
            self.result_text.see("end")
            self.result_text.configure(state="disabled")
        self.dialog.after(0, _do)
    
    def _set_status(self, text: str):
        
        def _do():
            self.status_label.configure(text=text)
        self.dialog.after(0, _do)
    
    def _start_diagnostics(self):
        
        self.result_text.configure(state="normal")
        self.result_text.delete("1.0", "end")
        self.result_text.configure(state="disabled")
        
        self.progress.start()
        self.btn_retry.configure(state="disabled")
        
        self._append_text("═" * 50)
        self._append_text("СИСТЕМНАЯ ИНФОРМАЦИЯ")
        self._append_text("═" * 50)
        sysinfo = self.diagnostics.get_system_info()
        self._append_text(sysinfo)
        
        self._append_text("")
        self._append_text(f"Сервер: {self.server.address}:{self.server.port}")
        self._append_text(f"Тип: {self.server.server_type}")
        self._append_text(f"Auth: {'***' if self.server.auth else 'нет'}")
        self._append_text(f"SNI: {self.server.sni or 'нет'}")
        self._append_text(f"Insecure: {self.server.insecure}")
        self._append_text("")
        
        def _on_step(step: str, result: str):
            def _do():
                self._set_status(f"⏳ {step}...")
                self._append_text("═" * 50)
                self._append_text(f"▶ {step.upper()}")
                self._append_text("═" * 50)
                self._append_text(result)
                self._append_text("")
            self.dialog.after(0, _do)
        
        def _on_done():
            def _do():
                self.progress.stop()
                self.progress.set(1)
                self._set_status("✅ Диагностика завершена")
                self.btn_retry.configure(state="normal")
            self.dialog.after(0, _do)
        
        self.diagnostics.run_full_diagnostics(
            self.server, self.config, _on_step, _on_done
        )
    
    def _copy_results(self):
        
        text = self.result_text.get("1.0", "end")
        self.dialog.clipboard_clear()
        self.dialog.clipboard_append(text)
        self.status_label.configure(text="✅ Скопировано в буфер обмена")