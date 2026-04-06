"""
main.py - Rested 진입점

아키텍처:
  - 메인 스레드 : Tkinter mainloop (위젯 + 팝업)
  - 데몬 스레드1: pystray 시스템 트레이
  - 데몬 스레드2: 복기 알림 스케줄러

트레이 / 스케줄러 → UI 호출은 반드시 root.after(0, fn) 로 메인 스레드에 위임.

실행 옵션:
  --test   시작 시 테스트 알림 다이얼로그 자동 표시
"""
import sys
import threading
from pathlib import Path

if getattr(sys, "frozen", False):
    _base = Path(sys.executable).parent
else:
    _base = Path(__file__).parent
sys.path.insert(0, str(_base))

import tkinter as tk
from tkinter import ttk

import database
import ui
from scheduler import ReviewScheduler
from widget import CompanWidget
from confirm_popup import show_confirm_popup

try:
    import pystray
    from PIL import Image, ImageDraw, ImageFont
    _HAS_TRAY = True
except ImportError:
    _HAS_TRAY = False

ICON_SIZE = 64


# ── 트레이 아이콘 이미지 ───────────────────────────────────

def _make_icon_image():
    icon_path = _base.parent / "assets" / "icon.png"
    if icon_path.exists():
        return Image.open(icon_path).convert("RGBA")

    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, ICON_SIZE - 4, ICON_SIZE - 4], fill="#3B82F6")
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    draw.text((ICON_SIZE // 2, ICON_SIZE // 2), "R",
              fill="white", font=font, anchor="mm")
    return img


# ── Dev Test: 링크 선택 → 즉시 알림 팝업 ─────────────────

def show_test_dialog(root: tk.Tk, on_confirm, on_badge_update):
    """등록된 링크 중 하나를 골라 즉시 확인 팝업을 띄움"""
    links = database.get_all_links()

    win = tk.Toplevel(root)
    win.title("🧪 테스트 알림")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    w, h = 400, 160
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    frame = ttk.Frame(win, padding=20)
    frame.pack(fill=tk.BOTH, expand=True)

    if not links:
        ttk.Label(frame, text="등록된 링크가 없습니다.\n먼저 링크를 추가해주세요.",
                  font=("Segoe UI", 10), justify="center").pack(expand=True)
        ttk.Button(frame, text="닫기", command=win.destroy, width=10).pack(pady=(12, 0))
        return

    ttk.Label(frame, text="테스트할 링크를 선택하세요",
              font=("Segoe UI", 10, "bold")).pack(anchor="w")

    # (id, url, title, added_at, pending, total)
    titles = [row[2] for row in links]
    choice_var = tk.StringVar(value=titles[0])
    combo = ttk.Combobox(frame, textvariable=choice_var, values=titles,
                         state="readonly", width=46)
    combo.pack(pady=(8, 16), fill=tk.X)

    def _run_test():
        idx = titles.index(choice_var.get())
        link_id, url, title, *_ = links[idx]
        win.destroy()
        # review_id=-1 은 테스트용 (confirm 시 DB에 쓰지 않음)
        show_confirm_popup(
            root, review_id=-1, url=url, title=title, interval_days=0,
            on_confirm=lambda rid: None,   # 테스트이므로 DB 변경 없음
            on_badge_update=on_badge_update,
        )

    btn_row = ttk.Frame(frame)
    btn_row.pack(fill=tk.X)
    ttk.Button(btn_row, text="테스트 실행", command=_run_test, width=14).pack(side=tk.RIGHT, padx=(4, 0))
    ttk.Button(btn_row, text="취소", command=win.destroy, width=10).pack(side=tk.RIGHT)

    win.bind("<Return>", lambda e: _run_test())
    win.bind("<Escape>", lambda e: win.destroy())


# ── 트레이 메뉴 ───────────────────────────────────────────

def _build_tray_menu(root: tk.Tk, widget: CompanWidget,
                     scheduler: ReviewScheduler):

    def _toggle_widget(icon, item):
        root.after(0, widget.toggle)

    def _show_list(icon, item):
        def _open():
            links = database.get_all_links()
            ui.show_link_list_dialog(links, database.delete_link)
        root.after(0, _open)

    def _test_notify(icon, item):
        root.after(0, lambda: show_test_dialog(
            root,
            on_confirm=database.confirm_review,
            on_badge_update=widget.update_badge,
        ))

    def _quit(icon, item):
        scheduler.stop()
        icon.stop()
        root.after(0, root.quit)

    return pystray.Menu(
        pystray.MenuItem("위젯 열기 / 닫기", _toggle_widget, default=True),
        pystray.MenuItem("등록된 링크 보기", _show_list),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🧪 테스트 알림", _test_notify),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("종료", _quit),
    )


# ── 메인 진입 ─────────────────────────────────────────────

def main():
    _test_mode = "--test" in sys.argv

    database.init_db()

    root = tk.Tk()
    root.withdraw()
    root.title("Rested")

    widget = CompanWidget(root, on_add_callback=database.add_link)
    widget.set_db_callbacks(
        get_unconfirmed=database.get_unconfirmed_reviews,
        confirm_review=database.confirm_review,
    )
    widget.show()

    def on_review_due(review_id, url, title, interval_days):
        root.after(
            0,
            lambda: show_confirm_popup(
                root, review_id, url, title, interval_days,
                on_confirm=database.confirm_review,
                on_badge_update=widget.update_badge,
            ),
        )
        root.after(100, widget.update_badge)

    scheduler = ReviewScheduler(on_review_due=on_review_due)
    scheduler.start()

    if _HAS_TRAY:
        tray = pystray.Icon(
            "Rested", _make_icon_image(), "Rested - 복기 알림",
            _build_tray_menu(root, widget, scheduler),
        )
        threading.Thread(target=tray.run, daemon=True).start()
    else:
        print("[Rested] pystray/Pillow 미설치 — 트레이 없이 실행합니다.")

    # --test 플래그: 위젯이 뜨고 나서 500ms 후 테스트 다이얼로그 자동 표시
    if _test_mode:
        root.after(500, lambda: show_test_dialog(
            root,
            on_confirm=database.confirm_review,
            on_badge_update=widget.update_badge,
        ))

    try:
        root.mainloop()
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
