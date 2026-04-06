"""
ui.py - 링크 추가 / 링크 목록 Tkinter UI
"""
import tkinter as tk
from tkinter import ttk, messagebox
import threading
import webbrowser


def _fetch_title(url: str) -> str:
    """URL에서 페이지 제목을 가져옴. 실패 시 빈 문자열 반환."""
    try:
        import urllib.request
        from html.parser import HTMLParser

        class TitleParser(HTMLParser):
            def __init__(self):
                super().__init__()
                self._in_title = False
                self.title = ""

            def handle_starttag(self, tag, attrs):
                if tag.lower() == "title":
                    self._in_title = True

            def handle_endtag(self, tag):
                if tag.lower() == "title":
                    self._in_title = False

            def handle_data(self, data):
                if self._in_title:
                    self.title += data

        req = urllib.request.Request(
            url,
            headers={"User-Agent": "Mozilla/5.0"},
        )
        with urllib.request.urlopen(req, timeout=5) as resp:
            html = resp.read(8192).decode("utf-8", errors="ignore")
        parser = TitleParser()
        parser.feed(html)
        return parser.title.strip()
    except Exception:
        return ""


def show_add_link_dialog(on_add_callback):
    """링크 추가 다이얼로그. on_add_callback(url, title) 호출."""
    win = tk.Tk()
    win.title("Compan - 링크 추가")
    win.resizable(False, False)
    win.attributes("-topmost", True)

    # 창 중앙 배치
    win.update_idletasks()
    w, h = 460, 200
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    frame = ttk.Frame(win, padding=20)
    frame.pack(fill=tk.BOTH, expand=True)

    ttk.Label(frame, text="URL", font=("Segoe UI", 10, "bold")).grid(
        row=0, column=0, sticky="w"
    )
    url_var = tk.StringVar()
    url_entry = ttk.Entry(frame, textvariable=url_var, width=48)
    url_entry.grid(row=1, column=0, columnspan=2, pady=(4, 12), sticky="ew")
    url_entry.focus()

    ttk.Label(frame, text="제목 (선택 — 비워두면 자동 감지)", font=("Segoe UI", 10, "bold")).grid(
        row=2, column=0, sticky="w"
    )
    title_var = tk.StringVar()
    title_entry = ttk.Entry(frame, textvariable=title_var, width=48)
    title_entry.grid(row=3, column=0, columnspan=2, pady=(4, 16), sticky="ew")

    status_var = tk.StringVar()
    status_label = ttk.Label(frame, textvariable=status_var, foreground="gray")
    status_label.grid(row=4, column=0, sticky="w")

    def do_add():
        url = url_var.get().strip()
        if not url:
            messagebox.showwarning("입력 오류", "URL을 입력해주세요.", parent=win)
            return
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
            url_var.set(url)

        title = title_var.get().strip()

        def _run():
            if not title:
                status_var.set("제목 가져오는 중...")
                win.update_idletasks()
                fetched = _fetch_title(url)
                title_var.set(fetched)
            final_title = title_var.get().strip() or url
            try:
                on_add_callback(url, final_title)
                status_var.set("")
                win.after(0, win.destroy)
            except Exception as e:
                win.after(0, lambda: messagebox.showerror("오류", str(e), parent=win))

        threading.Thread(target=_run, daemon=True).start()

    btn_frame = ttk.Frame(frame)
    btn_frame.grid(row=4, column=1, sticky="e")
    ttk.Button(btn_frame, text="추가", command=do_add, width=10).pack(side=tk.RIGHT, padx=(4, 0))
    ttk.Button(btn_frame, text="취소", command=win.destroy, width=10).pack(side=tk.RIGHT)

    frame.columnconfigure(0, weight=1)
    win.bind("<Return>", lambda e: do_add())
    win.bind("<Escape>", lambda e: win.destroy())
    win.mainloop()


def show_link_list_dialog(links, on_delete_callback):
    """등록된 링크 목록 다이얼로그."""
    win = tk.Tk()
    win.title("Compan - 등록된 링크")
    win.attributes("-topmost", True)

    w, h = 640, 400
    x = (win.winfo_screenwidth() - w) // 2
    y = (win.winfo_screenheight() - h) // 2
    win.geometry(f"{w}x{h}+{x}+{y}")

    frame = ttk.Frame(win, padding=16)
    frame.pack(fill=tk.BOTH, expand=True)

    cols = ("title", "added_at", "pending")
    tree = ttk.Treeview(
        frame,
        columns=cols,
        show="headings",
        selectmode="browse",
    )
    tree.heading("title", text="제목")
    tree.heading("added_at", text="등록일")
    tree.heading("pending", text="남은 복기")
    tree.column("title", width=320)
    tree.column("added_at", width=140, anchor="center")
    tree.column("pending", width=80, anchor="center")

    scrollbar = ttk.Scrollbar(frame, orient=tk.VERTICAL, command=tree.yview)
    tree.configure(yscrollcommand=scrollbar.set)
    tree.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
    scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

    # (id, url, title, added_at, pending_reviews, total_reviews)
    id_map = {}
    for row in links:
        link_id, url, title, added_at, pending, total = row
        added_short = added_at[:10]
        iid = tree.insert("", tk.END, values=(title, added_short, f"{pending}/{total}"))
        id_map[iid] = (link_id, url)

    def open_selected(event=None):
        sel = tree.selection()
        if sel:
            webbrowser.open(id_map[sel[0]][1])

    def delete_selected():
        sel = tree.selection()
        if not sel:
            return
        link_id, url = id_map[sel[0]]
        if messagebox.askyesno("삭제 확인", f"삭제하시겠습니까?\n{url}", parent=win):
            on_delete_callback(link_id)
            tree.delete(sel[0])

    btn_frame = ttk.Frame(win, padding=(16, 0, 16, 12))
    btn_frame.pack(fill=tk.X)
    ttk.Button(btn_frame, text="열기", command=open_selected, width=10).pack(side=tk.LEFT, padx=(0, 4))
    ttk.Button(btn_frame, text="삭제", command=delete_selected, width=10).pack(side=tk.LEFT)
    ttk.Button(btn_frame, text="닫기", command=win.destroy, width=10).pack(side=tk.RIGHT)

    tree.bind("<Double-1>", open_selected)
    win.mainloop()
