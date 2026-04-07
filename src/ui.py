"""
ui.py - 링크 추가 / 링크 목록 다이얼로그 (CustomTkinter)

master(CTk root)를 받아 CTkToplevel로 생성 → wait_window로 모달 동작.
"""
import customtkinter as ctk
import threading
import webbrowser

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
ROW_H   = "#2e3450"


# ── 페이지 제목 자동 감지 (외부에서도 import) ──────────────

def _fetch_title(url: str) -> str:
    try:
        import urllib.request
        from html.parser import HTMLParser

        class _T(HTMLParser):
            def __init__(self):
                super().__init__()
                self._in = False
                self.title = ""
            def handle_starttag(self, tag, _): self._in = tag.lower() == "title"
            def handle_endtag(self, tag):
                if tag.lower() == "title": self._in = False
            def handle_data(self, data):
                if self._in: self.title += data

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=5) as r:
            html = r.read(8192).decode("utf-8", errors="ignore")
        p = _T(); p.feed(html)
        return p.title.strip()
    except Exception:
        return ""


# ── 링크 추가 다이얼로그 ──────────────────────────────────

def show_add_link_dialog(master, on_add_callback):
    win = ctk.CTkToplevel(master)
    win.title("Rested - 링크 추가")
    win.resizable(False, False)
    win.attributes("-topmost", True)
    win.configure(fg_color=BG)
    win.grab_set()

    w, h = 460, 190
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    frame = ctk.CTkFrame(win, fg_color=BG, corner_radius=0)
    frame.pack(fill="both", expand=True, padx=20, pady=20)

    ctk.CTkLabel(frame, text="URL",
                 font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                 text_color=SUB).grid(row=0, column=0, sticky="w")

    url_var = ctk.StringVar()
    url_entry = ctk.CTkEntry(
        frame, textvariable=url_var, width=400,
        placeholder_text="https://",
        fg_color=SURFACE, text_color=TEXT, border_width=0,
        corner_radius=8, height=34,
        font=ctk.CTkFont(family="Segoe UI", size=11),
    )
    url_entry.grid(row=1, column=0, columnspan=2, pady=(4, 14), sticky="ew")
    url_entry.focus_set()

    ctk.CTkLabel(frame, text="제목  (선택 — 비워두면 자동 감지)",
                 font=ctk.CTkFont(family="Segoe UI", size=11, weight="bold"),
                 text_color=SUB).grid(row=2, column=0, sticky="w")

    title_var = ctk.StringVar()
    title_entry = ctk.CTkEntry(
        frame, textvariable=title_var, width=400,
        fg_color=SURFACE, text_color=TEXT, border_width=0,
        corner_radius=8, height=34,
        font=ctk.CTkFont(family="Segoe UI", size=11),
    )
    title_entry.grid(row=3, column=0, columnspan=2, pady=(4, 16), sticky="ew")

    status_var = ctk.StringVar()
    status_lbl = ctk.CTkLabel(frame, textvariable=status_var,
                               text_color=SUB,
                               font=ctk.CTkFont(size=10))
    status_lbl.grid(row=4, column=0, sticky="w")

    def do_add():
        url = url_var.get().strip()
        if not url:
            status_var.set("URL을 입력해주세요.")
            status_lbl.configure(text_color=ERR)
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            url_var.set(url)

        title = title_var.get().strip()

        def _run():
            if not title:
                win.after(0, lambda: status_var.set("제목 가져오는 중…"))
                fetched = _fetch_title(url)
                title_var.set(fetched)
            final_title = title_var.get().strip() or url
            try:
                on_add_callback(url, final_title)
                win.after(0, win.destroy)
            except Exception as e:
                win.after(0, lambda: (status_var.set(f"오류: {e}"),
                                      status_lbl.configure(text_color=ERR)))

        threading.Thread(target=_run, daemon=True).start()

    btn_frame = ctk.CTkFrame(frame, fg_color="transparent", corner_radius=0)
    btn_frame.grid(row=4, column=1, sticky="e")

    ctk.CTkButton(btn_frame, text="추가", width=80, height=30,
                  corner_radius=8, fg_color=ACCENT, hover_color=ACH,
                  font=ctk.CTkFont(size=11, weight="bold"),
                  command=do_add).pack(side="right", padx=(4, 0))
    ctk.CTkButton(btn_frame, text="취소", width=70, height=30,
                  corner_radius=8, fg_color=SURFACE, hover_color=ROW_H,
                  text_color=TEXT, font=ctk.CTkFont(size=11),
                  command=win.destroy).pack(side="right")

    frame.columnconfigure(0, weight=1)
    win.bind("<Return>", lambda _: do_add())
    win.bind("<Escape>", lambda _: win.destroy())
    win.wait_window()


# ── 링크 목록 다이얼로그 ──────────────────────────────────

def show_link_list_dialog(master, get_links_fn, on_delete_callback):
    """
    get_links_fn : 인자 없는 callable → 링크 목록 반환 (database.get_all_links)
    on_delete_callback : callable(link_id)
    """
    win = ctk.CTkToplevel(master)
    win.title("Rested - 등록된 링크")
    win.attributes("-topmost", True)
    win.configure(fg_color=BG)

    w, h = 620, 420
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    # 상태
    delete_mode  = [False]
    check_vars:  dict = {}   # link_id → BooleanVar
    cb_widgets:  dict = {}   # link_id → CTkCheckBox
    row_frames:  list = []   # 생성한 행 프레임 목록 (안전한 cleanup용)
    last_ids:    list = []   # 마지막으로 그린 link_id 목록 (변경 감지용)

    # ── 헤더 ──────────────────────────────────────────────
    hdr = ctk.CTkFrame(win, fg_color=TITLE, corner_radius=0, height=44)
    hdr.pack(fill="x")
    hdr.pack_propagate(False)
    ctk.CTkLabel(hdr, text="  등록된 링크",
                 font=ctk.CTkFont(family="Segoe UI", size=13, weight="bold"),
                 text_color=TEXT).pack(side="left", padx=16)

    # ── 스크롤 목록 ────────────────────────────────────────
    scroll = ctk.CTkScrollableFrame(
        win, fg_color=BG,
        scrollbar_button_color=SURFACE,
        scrollbar_button_hover_color=ACCENT,
        corner_radius=0,
    )
    scroll.pack(fill="both", expand=True, padx=12, pady=(12, 0))

    def build_rows(links):
        check_vars.clear()
        cb_widgets.clear()
        # CTkScrollableFrame 내부 위젯을 건드리지 않고 직접 추적한 행만 제거
        for rf in row_frames:
            if rf.winfo_exists():
                rf.destroy()
        row_frames.clear()
        last_ids.clear()
        last_ids.extend(row[0] for row in links)

        for row in links:
            link_id, url, title, added_at, pending, total = row
            added_short = added_at[:10]
            pending_txt = f"{pending}/{total}"

            rf = ctk.CTkFrame(scroll, fg_color=SURFACE, corner_radius=8)
            rf.pack(fill="x", pady=3)
            row_frames.append(rf)

            # grid 레이아웃: col0=체크박스, col1=제목, col2=복기, col3=날짜
            inner = ctk.CTkFrame(rf, fg_color="transparent", corner_radius=0)
            inner.pack(fill="x", padx=10, pady=7)
            inner.columnconfigure(1, weight=1)

            # 체크박스 (col 0) — 기본 숨김
            var = ctk.BooleanVar(value=False)
            check_vars[link_id] = var
            cb = ctk.CTkCheckBox(
                inner, variable=var, text="",
                width=20, height=20,
                checkbox_width=18, checkbox_height=18,
                corner_radius=4,
                fg_color=ACCENT, hover_color=ACH, border_color=SUB,
            )
            cb.grid(row=0, column=0, padx=(0, 8), sticky="w")
            cb.grid_remove()
            cb_widgets[link_id] = cb

            # 제목 (col 1)
            lbl = ctk.CTkLabel(inner, text=title,
                                font=ctk.CTkFont(family="Segoe UI", size=11),
                                text_color=TEXT, anchor="w")
            lbl.grid(row=0, column=1, sticky="ew")
            lbl.bind("<Double-1>", lambda e, u=url: webbrowser.open(u))
            inner.bind("<Double-1>", lambda e, u=url: webbrowser.open(u))

            # 남은 복기 (col 2)
            ctk.CTkLabel(inner, text=pending_txt,
                          font=ctk.CTkFont(family="Segoe UI", size=10),
                          text_color=SUB if pending == 0 else ACCENT,
                          width=50, anchor="center").grid(row=0, column=2, padx=4)

            # 등록일 (col 3)
            ctk.CTkLabel(inner, text=added_short,
                          font=ctk.CTkFont(family="Segoe UI", size=10),
                          text_color=SUB, width=80, anchor="center").grid(row=0, column=3)

    build_rows(get_links_fn())

    def auto_refresh():
        """삭제 모드가 아닐 때 2초마다 변경 감지 후 갱신"""
        if not win.winfo_exists():
            return
        if not delete_mode[0]:
            current = get_links_fn()
            current_ids = [r[0] for r in current]
            if current_ids != last_ids:
                build_rows(current)
        win.after(2000, auto_refresh)

    win.after(2000, auto_refresh)

    # ── 버튼 바 ───────────────────────────────────────────
    bar = ctk.CTkFrame(win, fg_color=TITLE, corner_radius=0, height=50)
    bar.pack(fill="x", pady=(8, 0))
    bar.pack_propagate(False)

    inner_bar = ctk.CTkFrame(bar, fg_color="transparent", corner_radius=0)
    inner_bar.pack(expand=True, fill="both", padx=12)

    def enter_delete_mode():
        delete_mode[0] = True
        for cb in cb_widgets.values():
            cb.grid()
        btn_delete.configure(text="선택한 항목 삭제", command=confirm_delete,
                              fg_color="#991b1b", hover_color="#b91c1c", width=130)
        btn_cancel.pack(side="left", padx=(6, 0), pady=10)

    def exit_delete_mode():
        delete_mode[0] = False
        for var in check_vars.values():
            var.set(False)
        for cb in cb_widgets.values():
            cb.grid_remove()
        btn_delete.configure(text="삭제", command=enter_delete_mode,
                              fg_color="#7f1d1d", hover_color="#991b1b", width=70)
        btn_cancel.pack_forget()

    def confirm_delete():
        ids = [lid for lid, v in check_vars.items() if v.get()]
        if not ids:
            return
        for lid in ids:
            on_delete_callback(lid)
        build_rows(get_links_fn())
        exit_delete_mode()

    btn_delete = ctk.CTkButton(
        inner_bar, text="삭제", width=70, height=30,
        corner_radius=8, fg_color="#7f1d1d", hover_color="#991b1b",
        font=ctk.CTkFont(size=11), command=enter_delete_mode,
    )
    btn_delete.pack(side="left", pady=10)

    btn_cancel = ctk.CTkButton(
        inner_bar, text="취소", width=60, height=30,
        corner_radius=8, fg_color=SURFACE, hover_color=ROW_H,
        text_color=TEXT, font=ctk.CTkFont(size=11),
        command=exit_delete_mode,
    )
    # btn_cancel은 삭제 모드 진입 시에만 표시

    ctk.CTkButton(inner_bar, text="닫기", width=70, height=30,
                  corner_radius=8, fg_color=SURFACE, hover_color=ROW_H,
                  text_color=TEXT, font=ctk.CTkFont(size=11),
                  command=win.destroy).pack(side="right", pady=10)

    def on_escape(_=None):
        if delete_mode[0]:
            exit_delete_mode()
        else:
            win.destroy()

    win.bind("<Escape>", on_escape)
    win.wait_window()
