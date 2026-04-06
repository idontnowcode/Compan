"""
main.py - Rested 진입점

아키텍처:
  - 메인 스레드 : CTk mainloop (위젯 + 팝업)
  - 데몬 스레드1: pystray 시스템 트레이
  - 데몬 스레드2: 복기 알림 스케줄러

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

import customtkinter as ctk

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")

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
BG     = "#1c2033"
SURFACE = "#252a40"
ACCENT  = "#3b82f6"
TEXT    = "#e2e8f0"
SUB     = "#8b95a8"
ERR     = "#ef4444"


# ── 트레이 아이콘 이미지 ───────────────────────────────────

def _make_icon_image():
    icon_path = _base.parent / "assets" / "icon.png"
    if icon_path.exists():
        return Image.open(icon_path).convert("RGBA")

    img = Image.new("RGBA", (ICON_SIZE, ICON_SIZE), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    draw.ellipse([4, 4, ICON_SIZE - 4, ICON_SIZE - 4], fill="#3b82f6")
    try:
        font = ImageFont.truetype("arial.ttf", 36)
    except Exception:
        font = ImageFont.load_default()
    draw.text((ICON_SIZE // 2, ICON_SIZE // 2), "R",
              fill="white", font=font, anchor="mm")
    return img


# ── Dev Test 다이얼로그 ───────────────────────────────────

def show_test_dialog(root, on_confirm, on_badge_update):
    links = database.get_all_links()

    win = ctk.CTkToplevel(root)
    win.title("🧪 테스트 알림")
    win.resizable(False, False)
    win.attributes("-topmost", True)
    win.configure(fg_color=BG)
    win.grab_set()

    w, h = 400, 160
    win.geometry(f"{w}x{h}+"
                 f"{(win.winfo_screenwidth()-w)//2}+"
                 f"{(win.winfo_screenheight()-h)//2}")

    frame = ctk.CTkFrame(win, fg_color=BG, corner_radius=0)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    if not links:
        ctk.CTkLabel(frame,
                     text="등록된 링크가 없습니다.\n먼저 링크를 추가해주세요.",
                     font=ctk.CTkFont(family="Segoe UI", size=11),
                     text_color=SUB, justify="center").pack(expand=True)
        ctk.CTkButton(frame, text="닫기", width=80, height=30,
                      corner_radius=8, fg_color=SURFACE,
                      command=win.destroy).pack(pady=(12, 0))
        win.wait_window()
        return

    ctk.CTkLabel(frame, text="테스트할 링크를 선택하세요",
                 font=ctk.CTkFont(family="Segoe UI", size=12, weight="bold"),
                 text_color=TEXT).pack(anchor="w")

    titles = [row[2] for row in links]
    choice_var = ctk.StringVar(value=titles[0])
    ctk.CTkComboBox(
        frame, variable=choice_var, values=titles,
        state="readonly", width=360, height=32,
        corner_radius=8, border_width=0,
        fg_color=SURFACE, text_color=TEXT,
        button_color=ACCENT, button_hover_color="#2563eb",
        dropdown_fg_color=SURFACE, dropdown_text_color=TEXT,
        font=ctk.CTkFont(size=11),
    ).pack(pady=(8, 16), fill="x")

    def _run_test():
        idx = titles.index(choice_var.get())
        _, url, title, *_ = links[idx]
        win.destroy()
        show_confirm_popup(
            root, review_id=-1, url=url, title=title, interval_days=0,
            on_confirm=lambda _: None,
            on_badge_update=on_badge_update,
        )

    btn_row = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
    btn_row.pack(fill="x")
    ctk.CTkButton(btn_row, text="테스트 실행", width=110, height=30,
                  corner_radius=8, fg_color=ACCENT, hover_color="#2563eb",
                  font=ctk.CTkFont(size=11, weight="bold"),
                  command=_run_test).pack(side="right", padx=(4, 0))
    ctk.CTkButton(btn_row, text="취소", width=70, height=30,
                  corner_radius=8, fg_color=SURFACE, text_color=TEXT,
                  font=ctk.CTkFont(size=11),
                  command=win.destroy).pack(side="right")

    win.bind("<Return>", lambda _: _run_test())
    win.bind("<Escape>", lambda _: win.destroy())
    win.wait_window()


# ── 트레이 메뉴 ───────────────────────────────────────────

def _build_tray_menu(root, widget: CompanWidget, scheduler: ReviewScheduler):

    def _toggle_widget(icon, item):
        root.after(0, widget.toggle)

    def _show_list(icon, item):
        def _open():
            links = database.get_all_links()
            ui.show_link_list_dialog(root, links, database.delete_link)
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
        pystray.MenuItem("위젯 열기 / 닫기", _toggle_widget),
        pystray.MenuItem("등록된 링크 보기", _show_list, default=True),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("🧪 테스트 알림", _test_notify),
        pystray.Menu.SEPARATOR,
        pystray.MenuItem("종료", _quit),
    )


# ── 메인 ──────────────────────────────────────────────────

def main():
    _test_mode = "--test" in sys.argv

    database.init_db()

    root = ctk.CTk()
    root.withdraw()
    root.title("Rested")

    widget = CompanWidget(root, on_add_callback=database.add_link)
    widget.set_db_callbacks(
        get_unconfirmed=database.get_unconfirmed_reviews,
        confirm_review=database.confirm_review,
    )
    widget.show()

    def on_review_due(review_id, url, title, interval_days):
        root.after(0, lambda: show_confirm_popup(
            root, review_id, url, title, interval_days,
            on_confirm=database.confirm_review,
            on_badge_update=widget.update_badge,
        ))
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
