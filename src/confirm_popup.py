"""
confirm_popup.py - 복기 확인 팝업 (CustomTkinter)

알림 발생 시 화면 우측 하단에 스택으로 쌓이는 토스트형 팝업.
'✓ 열기 + 확인' → 브라우저 열기 + confirmed=1
'⏰ 3시간 후'   → 닫기만 (스케줄러가 3시간 후 재알림)
"""
import customtkinter as ctk
import webbrowser

BG     = "#1c2033"
TITLE  = "#13162b"
TEXT   = "#e2e8f0"
SUB    = "#8b95a8"
OK     = "#22c55e"
OKH    = "#16a34a"
SN     = "#334155"
SNH    = "#475569"

POPUP_W = 320
POPUP_H = 108
MARGIN  = 14
GAP     = 8

_active: list["ConfirmPopup"] = []


class ConfirmPopup:
    def __init__(self, root, review_id, url, title, interval_days,
                 on_confirm, on_badge_update):
        self._root = root
        self._review_id = review_id
        self._url = url
        self._on_confirm = on_confirm
        self._on_badge_update = on_badge_update

        _active.append(self)
        self._win = self._build(title, interval_days)

    def _build(self, title, interval_days):
        win = ctk.CTkToplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.configure(fg_color=BG)

        idx = _active.index(self)
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = sw - POPUP_W - MARGIN
        y = sh - MARGIN - (POPUP_H + GAP) * (idx + 1)
        win.geometry(f"{POPUP_W}x{POPUP_H}+{x}+{y}")

        # ── 헤더 ──────────────────────────────────────────
        header = ctk.CTkFrame(win, height=28, corner_radius=0, fg_color=TITLE)
        header.pack(fill="x")
        header.pack_propagate(False)

        badge = "🧪  테스트 알림" if interval_days == 0 else f"📖  {interval_days}일차 복기 알림"
        ctk.CTkLabel(
            header, text=f"  {badge}",
            font=ctk.CTkFont(family="Segoe UI", size=9, weight="bold"),
            text_color=SUB,
        ).pack(side="left")

        ctk.CTkButton(
            header, text="✕", width=28, height=22,
            corner_radius=6, fg_color="transparent",
            hover_color="#3a2a2a", text_color=SUB,
            font=ctk.CTkFont(size=10),
            command=self._snooze,
        ).pack(side="right", padx=(0, 2))

        # ── 본문 ──────────────────────────────────────────
        body = ctk.CTkFrame(win, fg_color=BG, corner_radius=0)
        body.pack(fill="both", expand=True, padx=12, pady=(8, 10))

        short = title if len(title) <= 38 else title[:36] + "…"
        ctk.CTkLabel(
            body, text=short, text_color=TEXT,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            anchor="w",
        ).pack(fill="x", pady=(0, 8))

        btn_row = ctk.CTkFrame(body, fg_color="transparent", corner_radius=0)
        btn_row.pack(fill="x")

        ctk.CTkButton(
            btn_row, text="✓  열기 + 확인",
            height=28, corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=10, weight="bold"),
            fg_color=OK, hover_color=OKH,
            command=self._confirm,
        ).pack(side="left", padx=(0, 6))

        ctk.CTkButton(
            btn_row, text="⏰  3시간 후",
            height=28, corner_radius=8,
            font=ctk.CTkFont(family="Segoe UI", size=10),
            fg_color=SN, hover_color=SNH, text_color=TEXT,
            command=self._snooze,
        ).pack(side="left")

        return win

    def _confirm(self):
        webbrowser.open(self._url)
        self._on_confirm(self._review_id)
        self._on_badge_update()
        self._close()

    def _snooze(self):
        self._close()

    def _close(self):
        if self in _active:
            _active.remove(self)
            self._restack()
        if self._win.winfo_exists():
            self._win.destroy()

    def _restack(self):
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        for i, p in enumerate(_active):
            x = sw - POPUP_W - MARGIN
            y = sh - MARGIN - (POPUP_H + GAP) * (i + 1)
            if p._win.winfo_exists():
                p._win.geometry(f"{POPUP_W}x{POPUP_H}+{x}+{y}")


def show_confirm_popup(root, review_id, url, title, interval_days,
                       on_confirm, on_badge_update):
    ConfirmPopup(root, review_id, url, title, interval_days,
                 on_confirm, on_badge_update)
