"""
widget.py - 플로팅 URL 입력 위젯 (CustomTkinter)
"""
import customtkinter as ctk
import tkinter as tk
import threading
import webbrowser
from ui import _fetch_title

# ── 색상 ──────────────────────────────────────────────────
BG      = "#1c2033"
SURFACE = "#252a40"
TITLE   = "#13162b"
ACCENT  = "#3b82f6"
ACH     = "#2563eb"   # accent hover
TEXT    = "#e2e8f0"
SUB     = "#8b95a8"
OK      = "#22c55e"
OKH     = "#16a34a"
ERR     = "#ef4444"
BADGE   = "#ef4444"
ROW_H   = "#2e3450"

WIDGET_W       = 300
WIDGET_H_BASE  = 76
WIDGET_H_PANEL = 240
R = 10   # 기본 corner radius


class CompanWidget:
    def __init__(self, root: ctk.CTk, on_add_callback):
        self._root = root
        self._on_add = on_add_callback
        self._win: ctk.CTkToplevel | None = None
        self._pinned = True
        self._drag_ox = self._drag_oy = 0
        self._panel_open = False
        self._feedback_mode = False
        self._saved_url = ""

        self._db_get_unconfirmed = None
        self._db_confirm = None

    def set_db_callbacks(self, get_unconfirmed, confirm_review):
        self._db_get_unconfirmed = get_unconfirmed
        self._db_confirm = confirm_review

    # ── 외부 API (스레드-안전) ────────────────────────────

    def show(self):       self._root.after(0, self._show)
    def hide(self):       self._root.after(0, self._hide)
    def toggle(self):     self._root.after(0, self._toggle)
    def update_badge(self): self._root.after(0, self._refresh_badge)

    # ── 내부 (메인 스레드) ───────────────────────────────

    def _show(self):
        if self._win and self._win.winfo_exists():
            self._win.deiconify(); self._win.lift(); return
        self._build()

    def _hide(self):
        if self._win and self._win.winfo_exists():
            self._win.withdraw()

    def _toggle(self):
        if self._win and self._win.winfo_exists():
            if self._win.state() == "withdrawn":
                self._win.deiconify(); self._win.lift()
            else:
                self._win.withdraw()
        else:
            self._build()

    # ── 창 생성 ───────────────────────────────────────────

    def _build(self):
        win = ctk.CTkToplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(fg_color=BG)
        win.resizable(False, False)

        sw = win.winfo_screenwidth()
        win.geometry(f"{WIDGET_W}x{WIDGET_H_BASE}+{sw - WIDGET_W - 24}+80")

        self._win = win
        self._build_titlebar(win)
        self._build_body(win)
        self._build_panel(win)
        self._panel_frame.pack_forget()

        win.bind("<FocusOut>", self._on_focus_out)
        self._refresh_badge()

    # ── 제목바 ────────────────────────────────────────────

    def _build_titlebar(self, win):
        bar = ctk.CTkFrame(win, height=32, corner_radius=0, fg_color=TITLE)
        bar.pack(fill="x")
        bar.pack_propagate(False)

        bar.bind("<ButtonPress-1>", self._drag_start)
        bar.bind("<B1-Motion>",     self._drag_move)

        lbl = ctk.CTkLabel(bar, text="  ◉  Rested",
                           font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                           text_color=TEXT, cursor="fleur")
        lbl.pack(side="left", padx=4)
        lbl.bind("<ButtonPress-1>", self._drag_start)
        lbl.bind("<B1-Motion>",     self._drag_move)

        # 닫기
        ctk.CTkButton(bar, text="✕", width=28, height=22,
                      corner_radius=6, fg_color="transparent",
                      hover_color="#3a2a2a", text_color=SUB,
                      font=ctk.CTkFont(size=11),
                      command=self._hide).pack(side="right", padx=(0, 4))

        # 핀
        self._btn_pin = ctk.CTkButton(
            bar, text="📌", width=28, height=22,
            corner_radius=6, fg_color="transparent",
            hover_color=SURFACE, text_color=TEXT,
            font=ctk.CTkFont(size=11),
            command=self._toggle_pin,
        )
        self._btn_pin.pack(side="right", padx=2)

        # 배지 (기본 숨김)
        self._badge_btn = ctk.CTkButton(
            bar, text="", width=28, height=18,
            corner_radius=9, fg_color=BADGE,
            hover_color="#c53030", text_color="white",
            font=ctk.CTkFont(size=10, weight="bold"),
            command=self._toggle_panel,
        )

    # ── URL 입력 ──────────────────────────────────────────

    def _build_body(self, win):
        body = ctk.CTkFrame(win, fg_color=BG, corner_radius=0)
        body.pack(fill="x", padx=10, pady=(8, 8))
        self._body_frame = body

        self._url_var = ctk.StringVar()
        self._entry = ctk.CTkEntry(
            body,
            textvariable=self._url_var,
            placeholder_text="URL 입력 후 Enter",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=SURFACE,
            text_color=TEXT,
            placeholder_text_color=SUB,
            border_width=0,
            corner_radius=8,
            height=34,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._entry.bind("<Return>", self._do_add)
        self._entry.bind("<Key>", self._on_entry_key)

        self._btn_add = ctk.CTkButton(
            body, text="+", width=34, height=34,
            corner_radius=8,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color=ACCENT, hover_color=ACH,
            command=self._do_add,
        )
        self._btn_add.pack(side="right")

    # ── 미확인 목록 패널 ──────────────────────────────────

    def _build_panel(self, win):
        self._panel_frame = ctk.CTkFrame(win, fg_color=TITLE, corner_radius=0)

        ctk.CTkLabel(
            self._panel_frame,
            text="미확인 복기",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=SUB,
        ).pack(anchor="w", padx=12, pady=(6, 2))

        self._list_scroll = ctk.CTkScrollableFrame(
            self._panel_frame,
            fg_color="transparent",
            scrollbar_button_color=SURFACE,
            scrollbar_button_hover_color=ACCENT,
            corner_radius=0,
        )
        self._list_scroll.pack(fill="both", expand=True, padx=6, pady=(0, 6))

    def _refresh_panel(self):
        for w in self._list_scroll.winfo_children():
            w.destroy()
        if not self._db_get_unconfirmed:
            return
        rows = self._db_get_unconfirmed()
        if not rows:
            ctk.CTkLabel(self._list_scroll, text="모두 확인했어요 ✓",
                         text_color=OK,
                         font=ctk.CTkFont(size=11)).pack(pady=10)
            return
        for review_id, url, title, days, _ in rows:
            self._add_panel_row(review_id, url, title)

    def _add_panel_row(self, review_id, url, title):
        row = ctk.CTkFrame(self._list_scroll, fg_color=SURFACE, corner_radius=8)
        row.pack(fill="x", pady=2)

        short = title if len(title) <= 26 else title[:24] + "…"
        ctk.CTkLabel(row, text=short, text_color=TEXT,
                     font=ctk.CTkFont(size=10), anchor="w",
                     cursor="hand2").pack(side="left", fill="x",
                                         expand=True, padx=(8, 4), pady=6)

        ctk.CTkButton(
            row, text="✓", width=30, height=24,
            corner_radius=6, font=ctk.CTkFont(size=11, weight="bold"),
            fg_color=OK, hover_color=OKH,
            command=lambda rid=review_id, u=url: self._confirm(rid, u),
        ).pack(side="right", padx=(0, 6), pady=4)

    def _toggle_panel(self):
        self._panel_open = not self._panel_open
        if self._panel_open:
            self._refresh_panel()
            self._panel_frame.pack(fill="both", expand=True)
            self._win.geometry(f"{WIDGET_W}x{WIDGET_H_PANEL}")
        else:
            self._panel_frame.pack_forget()
            self._win.geometry(f"{WIDGET_W}x{WIDGET_H_BASE}")

    def _confirm(self, review_id, url):
        webbrowser.open(url)
        if self._db_confirm:
            self._db_confirm(review_id)
        self._refresh_badge()
        self._refresh_panel()

    # ── 배지 ──────────────────────────────────────────────

    def _refresh_badge(self):
        if not self._win or not self._win.winfo_exists():
            return
        if not self._db_get_unconfirmed:
            return
        count = len(self._db_get_unconfirmed())
        if count > 0:
            self._badge_btn.configure(text=f" {count} ")
            self._badge_btn.pack(side="right", padx=(0, 2))
        else:
            self._badge_btn.pack_forget()
            if self._panel_open:
                self._toggle_panel()

    # ── 핀 토글 ───────────────────────────────────────────

    def _toggle_pin(self):
        self._pinned = not self._pinned
        self._win.attributes("-topmost", self._pinned)
        self._btn_pin.configure(
            text="📌" if self._pinned else "📍",
            text_color=TEXT if self._pinned else SUB,
        )

    def _on_focus_out(self, _e):
        if not self._pinned and self._win:
            self._win.after(150, self._maybe_hide)

    def _maybe_hide(self):
        if self._win and self._win.winfo_exists():
            if self._win.focus_get() is None:
                self._win.withdraw()

    # ── 링크 추가 ─────────────────────────────────────────

    def _on_entry_key(self, _e=None):
        if self._feedback_mode:
            self._reset_entry(self._saved_url)

    def _entry_feedback(self, msg, fg, bg):
        self._feedback_mode = True
        self._url_var.set(msg)
        self._entry.configure(text_color=fg, fg_color=bg, state="disabled")

    def _reset_entry(self, restore=""):
        self._feedback_mode = False
        self._entry.configure(text_color=TEXT, fg_color=SURFACE, state="normal")
        self._url_var.set(restore)
        if not restore:
            self._entry.focus_set()

    def _do_add(self, _e=None):
        if self._feedback_mode:
            return
        url = self._url_var.get().strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url

        self._saved_url = url
        self._entry_feedback("  가져오는 중…", SUB, SURFACE)
        self._btn_add.configure(state="disabled")

        def _run():
            try:
                title = _fetch_title(url) or url
                self._on_add(url, title)
                self._win.after(0, self._on_success)
            except Exception as e:
                self._win.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _on_success(self):
        self._entry_feedback("✓  등록 완료!", OK, "#162d1f")
        self._btn_add.configure(state="normal")
        self._win.after(2200, self._reset_entry)

    def _on_error(self, msg):
        short = msg[:32] if len(msg) > 32 else msg
        self._entry_feedback(f"⚠  {short}", ERR, "#2d1616")
        self._btn_add.configure(state="normal")
        self._win.after(3000, lambda: self._reset_entry(self._saved_url))

    # ── 드래그 ────────────────────────────────────────────

    def _drag_start(self, e):
        self._drag_ox = e.x_root - self._win.winfo_x()
        self._drag_oy = e.y_root - self._win.winfo_y()

    def _drag_move(self, e):
        self._win.geometry(f"+{e.x_root - self._drag_ox}+{e.y_root - self._drag_oy}")
