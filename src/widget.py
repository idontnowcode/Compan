"""
widget.py - 플로팅 URL 입력 위젯
스티커 메모처럼 화면에 고정/비고정할 수 있는 항상-위 창
"""
import tkinter as tk
import threading
from ui import _fetch_title


# ── 색상 테마 ──────────────────────────────────────────────
BG          = "#1E293B"   # 본문 배경 (다크 네이비)
TITLEBAR    = "#0F172A"   # 제목바 배경
ACCENT      = "#3B82F6"   # 파란 포인트
ACCENT_HOV  = "#2563EB"   # 버튼 호버
ENTRY_BG    = "#334155"   # 입력창 배경
TEXT        = "#F1F5F9"   # 기본 텍스트
SUBTEXT     = "#94A3B8"   # 보조 텍스트
SUCCESS     = "#22C55E"
ERROR       = "#EF4444"

WIDGET_W    = 300
WIDGET_H    = 110


def _bind_hover(btn: tk.Widget, normal: str, hover: str):
    btn.bind("<Enter>", lambda _: btn.config(bg=hover))
    btn.bind("<Leave>", lambda _: btn.config(bg=normal))


class CompanWidget:
    """
    pystray 트레이 스레드와 Tkinter 메인 스레드에서 모두
    안전하게 제어할 수 있도록 root.after() 로 UI 조작.
    """

    def __init__(self, root: tk.Tk, on_add_callback):
        self._root = root
        self._on_add = on_add_callback
        self._win: tk.Toplevel | None = None
        self._pinned = True          # 고정 여부
        self._drag_ox = self._drag_oy = 0

    # ── 외부 API ──────────────────────────────────────────
    def show(self):
        self._root.after(0, self._show)

    def hide(self):
        self._root.after(0, self._hide)

    def toggle(self):
        self._root.after(0, self._toggle)

    # ── 내부 구현 (메인 스레드 전용) ──────────────────────

    def _show(self):
        if self._win and self._win.winfo_exists():
            self._win.deiconify()
            self._win.lift()
            return
        self._build()

    def _hide(self):
        if self._win and self._win.winfo_exists():
            self._win.withdraw()

    def _toggle(self):
        if self._win and self._win.winfo_exists():
            if self._win.state() == "withdrawn":
                self._win.deiconify()
                self._win.lift()
            else:
                self._win.withdraw()
        else:
            self._build()

    # ── 창 생성 ───────────────────────────────────────────

    def _build(self):
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)          # 프레임 제거
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.97)
        win.configure(bg=BG)
        win.resizable(False, False)

        # 화면 우측 상단 배치
        sw = win.winfo_screenwidth()
        win.geometry(f"{WIDGET_W}x{WIDGET_H}+{sw - WIDGET_W - 24}+80")

        self._win = win
        self._build_titlebar(win)
        self._build_body(win)

        # 비고정 상태일 때 포커스 잃으면 자동 숨기기
        win.bind("<FocusOut>", self._on_focus_out)

    # ── 제목바 ────────────────────────────────────────────

    def _build_titlebar(self, win: tk.Toplevel):
        bar = tk.Frame(win, bg=TITLEBAR, height=30, cursor="fleur")
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        # 드래그
        bar.bind("<ButtonPress-1>",  self._drag_start)
        bar.bind("<B1-Motion>",      self._drag_move)

        # 앱 이름
        lbl = tk.Label(bar, text=" ◉  Compan", bg=TITLEBAR, fg=TEXT,
                       font=("Segoe UI", 9, "bold"), cursor="fleur")
        lbl.pack(side=tk.LEFT, padx=6)
        lbl.bind("<ButtonPress-1>", self._drag_start)
        lbl.bind("<B1-Motion>",     self._drag_move)

        # 닫기 버튼
        self._btn_close = tk.Button(
            bar, text="✕", bg=TITLEBAR, fg=SUBTEXT,
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            width=3, command=self._hide,
        )
        self._btn_close.pack(side=tk.RIGHT, padx=2)
        _bind_hover(self._btn_close, TITLEBAR, "#475569")

        # 핀 버튼
        self._btn_pin = tk.Button(
            bar, text="📌", bg=TITLEBAR, fg=TEXT,
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            width=3, command=self._toggle_pin,
        )
        self._btn_pin.pack(side=tk.RIGHT, padx=2)
        _bind_hover(self._btn_pin, TITLEBAR, "#475569")
        self._refresh_pin_btn()

    # ── 본문 ──────────────────────────────────────────────

    def _build_body(self, win: tk.Toplevel):
        body = tk.Frame(win, bg=BG, padx=12, pady=8)
        body.pack(fill=tk.BOTH, expand=True)

        hint = tk.Label(body, text="URL을 입력하고 Enter", bg=BG, fg=SUBTEXT,
                        font=("Segoe UI", 8))
        hint.pack(anchor="w")

        row = tk.Frame(body, bg=BG)
        row.pack(fill=tk.X, pady=(4, 0))

        self._url_var = tk.StringVar()
        self._entry = tk.Entry(
            row, textvariable=self._url_var,
            font=("Segoe UI", 10), relief="flat",
            bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
        )
        self._entry.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=5, padx=(0, 6))
        self._entry.bind("<Return>", self._do_add)
        self._entry.focus_set()

        self._btn_add = tk.Button(
            row, text="추가", font=("Segoe UI", 9, "bold"),
            bg=ACCENT, fg="white", relief="flat", cursor="hand2",
            padx=10, command=self._do_add,
        )
        self._btn_add.pack(side=tk.RIGHT)
        _bind_hover(self._btn_add, ACCENT, ACCENT_HOV)

        self._status_var = tk.StringVar()
        self._status_lbl = tk.Label(
            body, textvariable=self._status_var,
            bg=BG, fg=SUBTEXT, font=("Segoe UI", 8),
        )
        self._status_lbl.pack(anchor="w", pady=(4, 0))

    # ── 핀 토글 ───────────────────────────────────────────

    def _toggle_pin(self):
        self._pinned = not self._pinned
        if self._win:
            self._win.attributes("-topmost", self._pinned)
        self._refresh_pin_btn()

    def _refresh_pin_btn(self):
        if not hasattr(self, "_btn_pin"):
            return
        if self._pinned:
            self._btn_pin.config(text="📌", fg=TEXT)
        else:
            self._btn_pin.config(text="📍", fg=SUBTEXT)

    def _on_focus_out(self, _event):
        """비고정 상태에서 포커스를 잃으면 자동으로 숨김"""
        if not self._pinned and self._win:
            self._win.after(150, self._maybe_hide)

    def _maybe_hide(self):
        """포커스가 위젯 내부 어디에도 없을 때만 숨김"""
        if self._win and self._win.winfo_exists():
            focused = self._win.focus_get()
            if focused is None:
                self._win.withdraw()

    # ── 링크 추가 ─────────────────────────────────────────

    def _do_add(self, _event=None):
        url = self._url_var.get().strip()
        if not url:
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            self._url_var.set(url)

        self._set_status("제목 가져오는 중…", SUBTEXT)
        self._btn_add.config(state="disabled")

        def _run():
            try:
                title = _fetch_title(url) or url
                self._on_add(url, title)
                self._win.after(0, self._on_success)
            except Exception as e:
                self._win.after(0, lambda: self._on_error(str(e)))

        threading.Thread(target=_run, daemon=True).start()

    def _on_success(self):
        self._url_var.set("")
        self._set_status("✓ 등록 완료!", SUCCESS)
        self._btn_add.config(state="normal")
        self._win.after(2500, lambda: self._set_status("", SUBTEXT))

    def _on_error(self, msg: str):
        self._set_status(f"오류: {msg}", ERROR)
        self._btn_add.config(state="normal")

    def _set_status(self, msg: str, color: str):
        self._status_var.set(msg)
        self._status_lbl.config(fg=color)

    # ── 드래그 ────────────────────────────────────────────

    def _drag_start(self, event: tk.Event):
        self._drag_ox = event.x_root - self._win.winfo_x()
        self._drag_oy = event.y_root - self._win.winfo_y()

    def _drag_move(self, event: tk.Event):
        x = event.x_root - self._drag_ox
        y = event.y_root - self._drag_oy
        self._win.geometry(f"+{x}+{y}")
