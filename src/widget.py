"""
widget.py - 플로팅 URL 입력 위젯 (CustomTkinter)

레이아웃:
  [제목바]
  [URL 입력 + + 버튼]
  [알람 토글 바]        ← 미확인 알람이 있을 때만 표시
  [알람 목록 패널]      ← 토글 바 클릭으로 열고 닫음
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
ACH     = "#2563eb"
TEXT    = "#e2e8f0"
SUB     = "#8b95a8"
OK      = "#22c55e"
OKH     = "#16a34a"
ERR     = "#ef4444"
ALARM_BAR = "#1a2540"   # 알람 토글 바 배경

WIDGET_W          = 300
WIDGET_H_BASE     = 76   # 알람 없음
WIDGET_H_TOGGLE   = 106  # 알람 있음 (토글 바만)
WIDGET_H_PANEL    = 310  # 알람 패널 열림


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

    def show(self):         self._root.after(0, self._show)
    def hide(self):         self._root.after(0, self._hide)
    def toggle(self):       self._root.after(0, self._toggle)
    def update_badge(self): self._root.after(0, self._refresh_alarm_bar)

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
        self._build_alarm_toggle(win)
        self._build_panel(win)

        # 초기 상태: 토글 바 & 패널 숨김
        self._alarm_toggle.pack_forget()
        self._panel_frame.pack_forget()

        win.bind("<FocusOut>", self._on_focus_out)
        self._refresh_alarm_bar()

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

        ctk.CTkButton(bar, text="✕", width=28, height=22,
                      corner_radius=6, fg_color="transparent",
                      hover_color="#3a2a2a", text_color=SUB,
                      font=ctk.CTkFont(size=11),
                      command=self._hide).pack(side="right", padx=(0, 4))

        self._btn_pin = ctk.CTkButton(
            bar, text="📌", width=28, height=22,
            corner_radius=6, fg_color="transparent",
            hover_color=SURFACE, text_color=TEXT,
            font=ctk.CTkFont(size=11),
            command=self._toggle_pin,
        )
        self._btn_pin.pack(side="right", padx=2)

    # ── URL 입력 ──────────────────────────────────────────

    def _build_body(self, win):
        body = ctk.CTkFrame(win, fg_color=BG, corner_radius=0)
        body.pack(fill="x", padx=10, pady=(8, 8))

        self._url_var = ctk.StringVar()
        self._entry = ctk.CTkEntry(
            body,
            textvariable=self._url_var,
            placeholder_text="URL 입력 후 Enter",
            font=ctk.CTkFont(family="Segoe UI", size=11),
            fg_color=SURFACE, text_color=TEXT,
            placeholder_text_color=SUB,
            border_width=0, corner_radius=8, height=34,
        )
        self._entry.pack(side="left", fill="x", expand=True, padx=(0, 6))
        self._entry.bind("<Return>", self._do_add)
        self._entry.bind("<Key>",    self._on_entry_key)

        self._btn_add = ctk.CTkButton(
            body, text="+", width=34, height=34,
            corner_radius=8,
            font=ctk.CTkFont(size=20, weight="bold"),
            fg_color=ACCENT, hover_color=ACH,
            command=self._do_add,
        )
        self._btn_add.pack(side="right")

        self._feedback_mode = False
        self._saved_url = ""

    # ── 알람 토글 바 ──────────────────────────────────────

    def _build_alarm_toggle(self, win):
        """URL 입력 아래 알람 토글 섹션 (미확인 알람 있을 때만 표시)"""
        bar = ctk.CTkFrame(win, fg_color=ALARM_BAR, corner_radius=0, height=30)
        bar.pack_propagate(False)
        self._alarm_toggle = bar

        self._alarm_toggle_lbl = ctk.CTkLabel(
            bar, text="",
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            text_color=ACCENT,
        )
        self._alarm_toggle_lbl.pack(side="left", padx=12)

        self._alarm_arrow = ctk.CTkLabel(
            bar, text="▼",
            font=ctk.CTkFont(size=9),
            text_color=SUB,
        )
        self._alarm_arrow.pack(side="right", padx=10)

        # 클릭으로 패널 토글
        for w in (bar, self._alarm_toggle_lbl, self._alarm_arrow):
            w.bind("<Button-1>", lambda _: self._toggle_panel())
            w.configure(cursor="hand2")

    # ── 알람 패널 ─────────────────────────────────────────

    def _build_panel(self, win):
        self._panel_frame = ctk.CTkScrollableFrame(
            win,
            fg_color=TITLE,
            scrollbar_button_color=SURFACE,
            scrollbar_button_hover_color=ACCENT,
            corner_radius=0,
        )

    def _refresh_panel(self):
        for w in self._panel_frame.winfo_children():
            w.destroy()

        if not self._db_get_unconfirmed:
            return

        rows = self._db_get_unconfirmed()
        if not rows:
            ctk.CTkLabel(self._panel_frame,
                         text="미확인 알람이 없습니다 ✓",
                         text_color=OK,
                         font=ctk.CTkFont(size=10)).pack(pady=14)
            return

        for review_id, url, title, days, _ in rows:
            self._add_alarm_row(review_id, url, title, days)

    def _add_alarm_row(self, review_id, url, title, days):
        row = ctk.CTkFrame(self._panel_frame, fg_color=SURFACE, corner_radius=8)
        row.pack(fill="x", pady=2, padx=4)

        # 왼쪽: 제목 + URL
        left = ctk.CTkFrame(row, fg_color="transparent", corner_radius=0)
        left.pack(side="left", fill="x", expand=True, padx=(10, 6), pady=8)

        short_title = title if len(title) <= 24 else title[:22] + "…"
        ctk.CTkLabel(left, text=short_title, text_color=TEXT,
                     font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
                     anchor="w").pack(fill="x")

        short_url = url if len(url) <= 32 else url[:30] + "…"
        url_lbl = ctk.CTkLabel(left, text=short_url, text_color=SUB,
                                font=ctk.CTkFont(family="Segoe UI", size=9),
                                anchor="w", cursor="hand2")
        url_lbl.pack(fill="x")
        url_lbl.bind("<Button-1>", lambda _, u=url: webbrowser.open(u))

        # 오른쪽: 복기 완료 버튼
        ctk.CTkButton(
            row, text="완료", width=46, height=30,
            corner_radius=6,
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            fg_color=OK, hover_color=OKH,
            command=lambda rid=review_id: self._confirm(rid),
        ).pack(side="right", padx=(0, 8), pady=8)

    # ── 알람 바 / 패널 갱신 ───────────────────────────────

    def _refresh_alarm_bar(self):
        if not self._win or not self._win.winfo_exists():
            return
        if not self._db_get_unconfirmed:
            return

        count = len(self._db_get_unconfirmed())

        if count > 0:
            self._alarm_toggle_lbl.configure(text=f"📋  미확인 알람  {count}건")
            # 토글 바가 숨겨져 있으면 표시
            if not self._alarm_toggle.winfo_ismapped():
                self._alarm_toggle.pack(fill="x", after=self._get_body_frame())
                if not self._panel_open:
                    self._set_height(WIDGET_H_TOGGLE)
        else:
            # 알람 없으면 패널 닫고 토글 바 숨김
            if self._panel_open:
                self._panel_frame.pack_forget()
                self._panel_open = False
            self._alarm_toggle.pack_forget()
            self._set_height(WIDGET_H_BASE)

        if self._panel_open:
            self._refresh_panel()

    def _get_body_frame(self):
        """body frame 참조 반환 (pack after 기준점)"""
        for w in self._win.winfo_children():
            if isinstance(w, ctk.CTkFrame) and w != self._alarm_toggle \
                    and w != self._panel_frame:
                # titlebar 이후 body frame
                children = self._win.winfo_children()
                idx = children.index(w)
                if idx == 1:
                    return w
        return None

    def _toggle_panel(self):
        if not self._win or not self._win.winfo_exists():
            return

        self._panel_open = not self._panel_open
        if self._panel_open:
            self._refresh_panel()
            self._panel_frame.pack(fill="both", expand=True)
            self._alarm_arrow.configure(text="▲")
            self._set_height(WIDGET_H_PANEL)
        else:
            self._panel_frame.pack_forget()
            self._alarm_arrow.configure(text="▼")
            self._set_height(WIDGET_H_TOGGLE)

    def _set_height(self, h):
        x = self._win.winfo_x()
        y = self._win.winfo_y()
        self._win.geometry(f"{WIDGET_W}x{h}+{x}+{y}")

    def _confirm(self, review_id):
        if self._db_confirm:
            self._db_confirm(review_id)
        self._refresh_alarm_bar()

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
