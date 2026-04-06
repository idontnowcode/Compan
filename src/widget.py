"""
widget.py - 플로팅 URL 입력 위젯
스티커 메모처럼 화면에 고정/비고정할 수 있는 항상-위 창.
미확인 복기가 있으면 배지로 표시하고, 클릭하면 확인 목록을 펼침.
"""
import tkinter as tk
import webbrowser
import threading
from ui import _fetch_title


# ── 색상 테마 ──────────────────────────────────────────────
BG          = "#1E293B"
TITLEBAR    = "#0F172A"
ACCENT      = "#3B82F6"
ACCENT_HOV  = "#2563EB"
ENTRY_BG    = "#334155"
TEXT        = "#F1F5F9"
SUBTEXT     = "#94A3B8"
SUCCESS     = "#22C55E"
SUCCESS_HOV = "#16A34A"
ERROR       = "#EF4444"
BADGE_BG    = "#EF4444"
PANEL_BG    = "#0F172A"
ROW_BG      = "#1E293B"
ROW_HOV     = "#334155"

WIDGET_W    = 300
WIDGET_H_BASE   = 110   # URL 입력만 있을 때
WIDGET_H_PANEL  = 260   # 미확인 목록 펼쳤을 때


def _bind_hover(w: tk.Widget, n: str, h: str):
    w.bind("<Enter>", lambda _: w.config(bg=h))
    w.bind("<Leave>", lambda _: w.config(bg=n))


class CompanWidget:
    def __init__(self, root: tk.Tk, on_add_callback):
        self._root = root
        self._on_add = on_add_callback
        self._win: tk.Toplevel | None = None
        self._pinned = True
        self._drag_ox = self._drag_oy = 0
        self._panel_open = False

        # DB 함수는 main.py 에서 주입 (순환 import 방지)
        self._db_get_unconfirmed = None
        self._db_confirm = None

    def set_db_callbacks(self, get_unconfirmed, confirm_review):
        self._db_get_unconfirmed = get_unconfirmed
        self._db_confirm = confirm_review

    # ── 외부 API (스레드-안전) ────────────────────────────

    def show(self):
        self._root.after(0, self._show)

    def hide(self):
        self._root.after(0, self._hide)

    def toggle(self):
        self._root.after(0, self._toggle)

    def update_badge(self):
        """스케줄러/팝업에서 확인 후 배지 갱신 요청"""
        self._root.after(0, self._refresh_badge)

    # ── 내부 구현 (메인 스레드) ───────────────────────────

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
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.97)
        win.configure(bg=BG)
        win.resizable(False, False)

        sw = win.winfo_screenwidth()
        win.geometry(f"{WIDGET_W}x{WIDGET_H_BASE}+{sw - WIDGET_W - 24}+80")

        self._win = win
        self._build_titlebar(win)
        self._build_body(win)
        self._build_panel(win)       # 접힌 상태로 생성
        self._panel_frame.pack_forget()

        win.bind("<FocusOut>", self._on_focus_out)
        self._refresh_badge()

    # ── 제목바 ────────────────────────────────────────────

    def _build_titlebar(self, win):
        bar = tk.Frame(win, bg=TITLEBAR, height=30, cursor="fleur")
        bar.pack(fill=tk.X)
        bar.pack_propagate(False)

        bar.bind("<ButtonPress-1>", self._drag_start)
        bar.bind("<B1-Motion>",     self._drag_move)

        lbl = tk.Label(bar, text=" ◉  Compan", bg=TITLEBAR, fg=TEXT,
                       font=("Segoe UI", 9, "bold"), cursor="fleur")
        lbl.pack(side=tk.LEFT, padx=6)
        lbl.bind("<ButtonPress-1>", self._drag_start)
        lbl.bind("<B1-Motion>",     self._drag_move)

        # 닫기
        self._btn_close = tk.Button(
            bar, text="✕", bg=TITLEBAR, fg=SUBTEXT,
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            width=3, command=self._hide,
        )
        self._btn_close.pack(side=tk.RIGHT, padx=2)
        _bind_hover(self._btn_close, TITLEBAR, "#475569")

        # 핀
        self._btn_pin = tk.Button(
            bar, text="📌", bg=TITLEBAR, fg=TEXT,
            font=("Segoe UI", 9), relief="flat", cursor="hand2",
            width=3, command=self._toggle_pin,
        )
        self._btn_pin.pack(side=tk.RIGHT, padx=2)
        _bind_hover(self._btn_pin, TITLEBAR, "#475569")
        self._refresh_pin_btn()

        # 미확인 배지 버튼 (기본 숨김)
        self._badge_btn = tk.Button(
            bar, text="", bg=BADGE_BG, fg="white",
            font=("Segoe UI", 8, "bold"), relief="flat", cursor="hand2",
            padx=5, command=self._toggle_panel,
        )
        # pack은 _refresh_badge 에서 처리

    # ── URL 입력 본문 ──────────────────────────────────────

    def _build_body(self, win):
        body = tk.Frame(win, bg=BG, padx=12, pady=8)
        body.pack(fill=tk.X)
        self._body_frame = body

        tk.Label(body, text="URL을 입력하고 Enter", bg=BG, fg=SUBTEXT,
                 font=("Segoe UI", 8)).pack(anchor="w")

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

    # ── 미확인 목록 패널 ──────────────────────────────────

    def _build_panel(self, win):
        outer = tk.Frame(win, bg=PANEL_BG)
        self._panel_frame = outer

        # 패널 헤더
        hdr = tk.Frame(outer, bg=PANEL_BG, padx=10, pady=5)
        hdr.pack(fill=tk.X)
        self._panel_title = tk.Label(
            hdr, text="미확인 복기", bg=PANEL_BG, fg=TEXT,
            font=("Segoe UI", 9, "bold"),
        )
        self._panel_title.pack(side=tk.LEFT)

        # 스크롤 가능한 목록
        self._list_frame = tk.Frame(outer, bg=PANEL_BG)
        self._list_frame.pack(fill=tk.BOTH, expand=True, padx=6, pady=(0, 6))

    def _refresh_panel(self):
        """미확인 목록을 다시 그림"""
        for w in self._list_frame.winfo_children():
            w.destroy()

        if not self._db_get_unconfirmed:
            return

        rows = self._db_get_unconfirmed()
        if not rows:
            tk.Label(self._list_frame, text="모두 확인했어요 ✓",
                     bg=PANEL_BG, fg=SUCCESS, font=("Segoe UI", 9)).pack(pady=10)
            return

        for review_id, url, title, days, _ in rows:
            self._add_panel_row(review_id, url, title, days)

    def _add_panel_row(self, review_id, url, title, days):
        row = tk.Frame(self._list_frame, bg=ROW_BG, pady=4, padx=8, cursor="hand2")
        row.pack(fill=tk.X, pady=2)

        short = title if len(title) <= 28 else title[:26] + "…"
        tk.Label(row, text=short, bg=ROW_BG, fg=TEXT,
                 font=("Segoe UI", 9), anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)

        btn = tk.Button(
            row, text="✓", bg=SUCCESS, fg="white",
            font=("Segoe UI", 9, "bold"), relief="flat", cursor="hand2",
            padx=6,
            command=lambda rid=review_id, u=url: self._confirm(rid, u),
        )
        btn.pack(side=tk.RIGHT)
        _bind_hover(btn, SUCCESS, SUCCESS_HOV)

        for w in (row,):
            w.bind("<Double-1>", lambda e, u=url: webbrowser.open(u))
        _bind_hover(row, ROW_BG, ROW_HOV)

    def _toggle_panel(self):
        self._panel_open = not self._panel_open
        if self._panel_open:
            self._refresh_panel()
            self._panel_frame.pack(fill=tk.BOTH, expand=True)
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

    # ── 배지 갱신 ─────────────────────────────────────────

    def _refresh_badge(self):
        if not self._win or not self._win.winfo_exists():
            return
        if not self._db_get_unconfirmed:
            return

        count = len(self._db_get_unconfirmed())
        if count > 0:
            self._badge_btn.config(text=f" {count} ")
            self._badge_btn.pack(side=tk.RIGHT, padx=(0, 4))
        else:
            self._badge_btn.pack_forget()
            # 패널 열려 있으면 닫기
            if self._panel_open:
                self._toggle_panel()

    # ── 핀 토글 ───────────────────────────────────────────

    def _toggle_pin(self):
        self._pinned = not self._pinned
        if self._win:
            self._win.attributes("-topmost", self._pinned)
        self._refresh_pin_btn()

    def _refresh_pin_btn(self):
        if not hasattr(self, "_btn_pin"):
            return
        self._btn_pin.config(
            text="📌" if self._pinned else "📍",
            fg=TEXT if self._pinned else SUBTEXT,
        )

    def _on_focus_out(self, _event):
        if not self._pinned and self._win:
            self._win.after(150, self._maybe_hide)

    def _maybe_hide(self):
        if self._win and self._win.winfo_exists():
            if self._win.focus_get() is None:
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
