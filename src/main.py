"""
main.py - Compan 진입점
시스템 트레이 아이콘으로 백그라운드 실행
"""
import sys
import threading
from pathlib import Path

# PyInstaller 번들 시 src 디렉터리가 sys.path에 포함되도록
if getattr(sys, "frozen", False):
    base = Path(sys.executable).parent
else:
    base = Path(__file__).parent
sys.path.insert(0, str(base))

import database
import ui
from scheduler import ReviewScheduler

try:
    import pystray
    from PIL import Image, ImageDraw
except ImportError:
    pystray = None

ICON_SIZE = 64


def _create_icon_image() -> "Image.Image":
    """assets/icon.png가 없으면 간단한 아이콘 생성"""
    icon_path = base.parent / "assets" / "icon.png"
    if icon_path.exists():
        from PIL import Image
        return Image.open(icon_path).convert("RGBA")

    from PIL import Image, ImageDraw, ImageFont
    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    # 파란 원 배경
    draw.ellipse([4, 4, ICON_SIZE - 4, ICON_SIZE - 4], fill="#3B82F6")
    # 흰색 'C' 텍스트
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    draw.text((ICON_SIZE // 2, ICON_SIZE // 2), "C", fill="white", font=font, anchor="mm")
    return img


def _build_menu(scheduler: ReviewScheduler):
    def add_link_action(icon, item):
        threading.Thread(
            target=ui.show_add_link_dialog,
            args=(database.add_link,),
            daemon=True,
        ).start()

    def list_links_action(icon, item):
        links = database.get_all_links()
        threading.Thread(
            target=ui.show_link_list_dialog,
            args=(links, database.delete_link),
            daemon=True,
        ).start()

    def quit_action(icon, item):
        scheduler.stop()
        icon.stop()

    return pystray.Menu(
        pystray.MenuItem("링크 추가", add_link_action, default=True),
        pystray.MenuItem("등록된 링크 보기", list_links_action),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("종료", quit_action),
    )


def run_with_tray():
    database.init_db()
    scheduler = ReviewScheduler()
    scheduler.start()

    image = _create_icon_image()
    menu = _build_menu(scheduler)
    icon = pystray.Icon("Compan", image, "Compan - 복기 알림", menu)
    icon.run()


def run_headless():
    """pystray 없이 콘솔 모드로 실행 (개발/테스트용)"""
    import time
    database.init_db()
    scheduler = ReviewScheduler()
    scheduler.start()
    print("[Compan] 백그라운드 실행 중. Ctrl+C로 종료.")
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        scheduler.stop()
        print("[Compan] 종료.")


if __name__ == "__main__":
    if pystray is not None:
        run_with_tray()
    else:
        print("[Compan] pystray/Pillow 미설치 — 콘솔 모드로 실행합니다.")
        run_headless()
