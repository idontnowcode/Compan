"""
confirm_popup.py - 복기 확인 팝업

알림이 발생할 때마다 화면 우측 하단에서 스택으로 쌓이는 작은 팝업.
'열기 + 확인' → 브라우저 열기 + DB confirmed=1
'3시간 후'   → 팝업만 닫음 (DB는 그대로 → 스케줄러가 3시간 후 재알림)
"""
import tkinter as tk
import webbrowser

# ── 색상 ───────────────────────────────────────────────────
BG       = "#1E293B"
HEADER   = "#0F172A"
TEXT     = "#F1F5F9"
SUBTEXT  = "#94A3B8"
BTN_OK   = "#22C55E"
BTN_OK_H = "#16A34A"
BTN_SN   = "#475569"
BTN_SN_H = "#64748B"

POPUP_W = 320
POPUP_H = 110
MARGIN  = 12   # 화면 가장자리 여백
GAP     = 8    # 팝업 간 간격

# 현재 화면에 표시 중인 팝업 수 (스택 오프셋 계산용)
_active: list["ConfirmPopup"] = []


def _bind_hover(w: tk.Widget, n: str, h: str):
    w.bind("<Enter>", lambda _: w.config(bg=h))
    w.bind("<Leave>", lambda _: w.config(bg=n))


class ConfirmPopup:
    def __init__(
        self,
        root: tk.Tk,
        review_id: int,
        url: str,
        title: str,
        interval_days: int,
        on_confirm,   # callable(review_id)
        on_badge_update,  # callable() – 위젯 배지 갱신 요청
    ):
        self._root = root
        self._review_id = review_id
        self._url = url
        self._on_confirm = on_confirm
        self._on_badge_update = on_badge_update

        _active.append(self)
        self._win = self._build(title, interval_days)

    # ── 창 생성 ───────────────────────────────────────────

    def _build(self, title: str, interval_days: int) -> tk.Toplevel:
        win = tk.Toplevel(self._root)
        win.overrideredirect(True)
        win.attributes("-topmost", True)
        win.attributes("-alpha", 0.96)
        win.configure(bg=BG)

        # 위치: 화면 우측 하단, 스택 순서로 위로 쌓임
        idx = _active.index(self)
        sw = win.winfo_screenwidth()
        sh = win.winfo_screenheight()
        x = sw - POPUP_W - MARGIN
        y = sh - MARGIN - (POPUP_H + GAP) * (idx + 1)
        win.geometry(f"{POPUP_W}x{POPUP_H}+{x}+{y}")

        # ── 헤더 ──────────────────────────────────────────
        header = tk.Frame(win, bg=HEADER, height=26)
        header.pack(fill=tk.X)
        header.pack_propagate(False)

        tk.Label(
            header, text=f"  📖  {interval_days}일차 복기 알림",
            bg=HEADER, fg=TEXT, font=("Segoe UI", 8, "bold"),
        ).pack(side=tk.LEFT)

        tk.Button(
            header, text="✕", bg=HEADER, fg=SUBTEXT,
            font=("Segoe UI", 8), relief="flat", cursor="hand2", width=3,
            command=self._snooze,
        ).pack(side=tk.RIGHT)

        # ── 본문 ──────────────────────────────────────────
        body = tk.Frame(win, bg=BG, padx=12, pady=8)
        body.pack(fill=tk.BOTH, expand=True)

        # 제목 (길면 말줄임)
        short = title if len(title) <= 36 else title[:34] + "…"
        tk.Label(
            body, text=short, bg=BG, fg=TEXT,
            font=("Segoe UI", 9), anchor="w",
        ).pack(fill=tk.X)

        btn_row = tk.Frame(body, bg=BG)
        btn_row.pack(fill=tk.X, pady=(6, 0))

        btn_ok = tk.Button(
            btn_row, text="✓  열기 + 확인",
            bg=BTN_OK, fg="white", font=("Segoe UI", 9, "bold"),
            relief="flat", cursor="hand2", padx=8, pady=3,
            command=self._confirm,
        )
        btn_ok.pack(side=tk.LEFT, padx=(0, 6))
        _bind_hover(btn_ok, BTN_OK, BTN_OK_H)

        btn_sn = tk.Button(
            btn_row, text="⏰  3시간 후",
            bg=BTN_SN, fg=TEXT, font=("Segoe UI", 9),
            relief="flat", cursor="hand2", padx=8, pady=3,
            command=self._snooze,
        )
        btn_sn.pack(side=tk.LEFT)
        _bind_hover(btn_sn, BTN_SN, BTN_SN_H)

        return win

    # ── 버튼 핸들러 ───────────────────────────────────────

    def _confirm(self):
        webbrowser.open(self._url)
        self._on_confirm(self._review_id)
        self._on_badge_update()
        self._close()

    def _snooze(self):
        # last_notified_at 은 스케줄러가 이미 갱신해 둠 → 그냥 닫기
        self._close()

    def _close(self):
        if self in _active:
            _active.remove(self)
            self._restack()
        if self._win.winfo_exists():
            self._win.destroy()

    def _restack(self):
        """닫힌 팝업 아래에 있던 팝업들을 아래로 내림"""
        sw = self._win.winfo_screenwidth()
        sh = self._win.winfo_screenheight()
        for i, popup in enumerate(_active):
            x = sw - POPUP_W - MARGIN
            y = sh - MARGIN - (POPUP_H + GAP) * (i + 1)
            if popup._win.winfo_exists():
                popup._win.geometry(f"{POPUP_W}x{POPUP_H}+{x}+{y}")


def show_confirm_popup(root, review_id, url, title, interval_days,
                       on_confirm, on_badge_update):
    """메인 스레드에서 호출. root.after()로 감싸서 사용."""
    ConfirmPopup(root, review_id, url, title, interval_days,
                 on_confirm, on_badge_update)
