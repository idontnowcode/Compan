"""
main.py - Compan 진입점

아키텍처:
  - 메인 스레드 : Tkinter mainloop (숨겨진 root + 플로팅 위젯 / 다이얼로그)
  - 데몬 스레드1: pystray 시스템 트레이
  - 데몬 스레드2: 복기 알림 스케줄러

트레이 → UI 호출은 반드시 root.after(0, fn) 로 메인 스레드에 위임.
"""
import sys
import threading
from pathlib import Path

# PyInstaller 번들 환경에서 src 경로 보장
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

    # 숨겨진 Tkinter 루트 — mainloop 전용
    root = tk.Tk()
    root.withdraw()
    root.title("Compan")

    # 플로팅 위젯 생성 후 즉시 표시
    widget = CompanWidget(root, on_add_callback=database.add_link)
    widget.show()

    # 복기 스케줄러
    scheduler = ReviewScheduler()
    scheduler.start()

    if _HAS_TRAY:
        icon_img = _make_icon_image()
        menu = _build_tray_menu(root, widget, scheduler)
        tray = pystray.Icon("Compan", icon_img, "Compan - 복기 알림", menu)

        # pystray 를 데몬 스레드에서 실행
        tray_thread = threading.Thread(target=tray.run, daemon=True)
        tray_thread.start()
    else:
        print("[Compan] pystray/Pillow 미설치 — 트레이 없이 실행합니다.")

    try:
        root.mainloop()
    finally:
        scheduler.stop()


if __name__ == "__main__":
    main()
