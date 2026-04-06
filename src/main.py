"""
main.py - Compan 진입점

아키텍처:
  - 메인 스레드 : Tkinter mainloop (위젯 + 팝업)
  - 데몬 스레드1: pystray 시스템 트레이
  - 데몬 스레드2: 복기 알림 스케줄러

트레이 / 스케줄러 → UI 호출은 반드시 root.after(0, fn) 로 메인 스레드에 위임.
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
    draw.text((ICON_SIZE // 2, ICON_SIZE // 2), "C",
              fill="white", font=font, anchor="mm")
    return img


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

    def _quit(icon, item):
        scheduler.stop()
        icon.stop()
        root.after(0, root.quit)

    return pystray.Menu(
        pystray.MenuItem("위젯 열기 / 닫기", _toggle_widget, default=True),
        pystray.MenuItem("등록된 링크 보기", _show_list),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("종료", _quit),
    )


# ── 메인 진입 ─────────────────────────────────────────────

def main():
    database.init_db()

    root = tk.Tk()
    root.withdraw()
    root.title("Compan")

    # 위젯 생성 + DB 콜백 주입
    widget = CompanWidget(root, on_add_callback=database.add_link)
    widget.set_db_callbacks(
        get_unconfirmed=database.get_unconfirmed_reviews,
        confirm_review=database.confirm_review,
    )
    widget.show()

    def on_review_due(review_id, url, title, interval_days):
        """스케줄러 스레드에서 호출 → 메인 스레드로 팝업 위임"""
        root.after(
            0,
            lambda: show_confirm_popup(
                root, review_id, url, title, interval_days,
                on_confirm=database.confirm_review,
                on_badge_update=widget.update_badge,
            ),
        )
        # 위젯 배지도 갱신
        root.after(100, widget.update_badge)

    scheduler = ReviewScheduler(on_review_due=on_review_due)
    scheduler.start()

    if _HAS_TRAY:
        tray = pystray.Icon(
            "Compan", _make_icon_image(), "Compan - 복기 알림",
            _build_tray_menu(root, widget, scheduler),
        )
        threading.Thread(target=tray.run, daemon=True).start()
    else:
        print("[Compan] pystray/Pillow 미설치 — 트레이 없이 실행합니다.")

    try:
        root.mainloop()
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
