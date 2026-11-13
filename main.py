#!/usr/bin/env python3
"""Instagram Uploader for Linux (Arch) - Stories / Reels / Posts.

Uses the unofficial `instagrapi` library. The password is never stored;
only the session (cookies/tokens) is saved to the per-user config folder (Linux: ~/.config/insta-uploader,
Windows: %APPDATA%\\insta-uploader) with private permissions.
"""
import json
import os
import queue
import sys
import threading
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from instagrapi import Client

if sys.platform.startswith("win"):
    _base = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
elif sys.platform == "darwin":
    _base = Path.home() / "Library" / "Application Support"
else:
    _base = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
CONFIG_DIR = _base / "insta-uploader"
CONFIG_DIR.mkdir(parents=True, exist_ok=True)


def _private(path: Path, mode: int):
    try:
        os.chmod(path, mode)  # limited effect on Windows, harmless
    except OSError:
        pass


_private(CONFIG_DIR, 0o700)
LAST_USER_FILE = CONFIG_DIR / "last_user.txt"

IMG = (".jpg", ".jpeg", ".png")
VID = (".mp4", ".mov")


def session_path(username: str) -> Path:
    return CONFIG_DIR / f"{username}.json"


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Instagram Uploader (Linux)")
        self.geometry("560x520")
        self.cl = Client()
        self.cl.delay_range = [1, 3]
        self.username = ""
        self.files: list[str] = []
        self.cover = ""
        self.ui_queue: queue.Queue = queue.Queue()
        self.after(100, self._drain_queue)

        self.login_frame = ttk.Frame(self, padding=20)
        self.upload_frame = ttk.Frame(self, padding=15)
        self._build_login()
        self._build_upload()
        self.login_frame.pack(fill="both", expand=True)

        last = LAST_USER_FILE.read_text().strip() if LAST_USER_FILE.exists() else ""
        if last:
            self.user_entry.insert(0, last)
            if session_path(last).exists():
                self.status_login.set(f"Found saved session for '{last}'. Trying it...")
                self._run(self._try_session, last)

    # ---------- thread helpers ----------
    def _run(self, fn, *args):
        def target():
            try:
                fn(*args)
            except Exception as e:  # noqa: BLE001
                self.ui_queue.put(lambda e=e: self._error(str(e)))
        threading.Thread(target=target, daemon=True).start()

    def _drain_queue(self):
        try:
            while True:
                self.ui_queue.get_nowait()()
        except queue.Empty:
            pass
        self.after(100, self._drain_queue)

    def ui(self, fn):
        self.ui_queue.put(fn)

    def _error(self, msg):
        self.login_btn.config(state="normal")
        self.upload_btn.config(state="normal")
        self.progress.stop()
        self.status_up.set("Error: " + msg)
        messagebox.showerror("Error", msg)

    # ---------- login ----------
    def _build_login(self):
        f = self.login_frame
        ttk.Label(f, text="Instagram Uploader", font=("sans", 16, "bold")).pack(pady=10)
        ttk.Label(f, text="Username").pack()
        self.user_entry = ttk.Entry(f, width=32)
        self.user_entry.pack(pady=4)
        ttk.Label(f, text="Password").pack()
        self.pass_entry = ttk.Entry(f, width=32, show="*")
        self.pass_entry.pack(pady=4)
        ttk.Label(f, text="2FA code (only if enabled)").pack()
        self.code_entry = ttk.Entry(f, width=32)
        self.code_entry.pack(pady=4)
        ttk.Label(f, text="OR sessionid cookie (if password login is blocked)").pack()
        self.sid_entry = ttk.Entry(f, width=32, show="*")
        self.sid_entry.pack(pady=4)
        self.login_btn = ttk.Button(f, text="Login", command=self.do_login)
        self.login_btn.pack(pady=10)
        self.status_login = tk.StringVar()
        ttk.Label(f, textvariable=self.status_login, wraplength=480).pack()
        self.pass_entry.bind("<Return>", lambda _e: self.do_login())

    def do_login(self):
        u = self.user_entry.get().strip()
        p = self.pass_entry.get()
        code = self.code_entry.get().strip()
        sid = self.sid_entry.get().strip()
        if not u or not (p or sid):
            messagebox.showerror("Error", "Enter username + password, or username + sessionid.")
            return
        self.login_btn.config(state="disabled")
        self.status_login.set("Logging in...")
        if sid:
            self._run(self._login_sid_thread, u, sid)
        else:
            self._run(self._login_thread, u, p, code)

    def _login_sid_thread(self, u, sid):
        cl = Client()
        cl.delay_range = [1, 3]
        cl.login_by_sessionid(sid)
        self._save_session(cl, u)
        self.cl, self.username = cl, u
        self.ui(self._show_upload)

    def _login_thread(self, u, p, code):
        cl = Client()
        cl.delay_range = [1, 3]
        sp = session_path(u)
        if sp.exists():
            cl.set_settings(json.loads(sp.read_text()))
        cl.login(u, p, verification_code=code)
        self._save_session(cl, u)
        self.cl, self.username = cl, u
        self.ui(self._show_upload)

    def _try_session(self, u):
        cl = Client()
        cl.delay_range = [1, 3]
        cl.set_settings(json.loads(session_path(u).read_text()))
        try:
            cl.get_timeline_feed()  # validates the session
        except Exception:  # noqa: BLE001
            self.ui(lambda: self.status_login.set("Saved session expired. Please login again."))
            return
        self.cl, self.username = cl, u
        self.ui(self._show_upload)

    def _save_session(self, cl, u):
        sp = session_path(u)
        sp.write_text(json.dumps(cl.get_settings()))
        _private(sp, 0o600)
        LAST_USER_FILE.write_text(u)

    def logout(self):
        sp = session_path(self.username)
        if sp.exists():
            sp.unlink()
        self.pass_entry.delete(0, "end")
        self.upload_frame.pack_forget()
        self.login_btn.config(state="normal")
        self.status_login.set("Logged out, session removed.")
        self.login_frame.pack(fill="both", expand=True)

    # ---------- upload ----------
    def _build_upload(self):
        f = self.upload_frame
        self.who = tk.StringVar()
        ttk.Label(f, textvariable=self.who, font=("sans", 11, "bold")).pack(anchor="w")

        self.kind = tk.StringVar(value="Story")
        row = ttk.Frame(f)
        row.pack(fill="x", pady=8)
        for k in ("Story", "Reel", "Post"):
            ttk.Radiobutton(row, text=k, value=k, variable=self.kind).pack(side="left", padx=8)

        btns = ttk.Frame(f)
        btns.pack(fill="x")
        ttk.Button(btns, text="Select file(s)", command=self.pick_files).pack(side="left")
        ttk.Button(btns, text="Cover (optional)", command=self.pick_cover).pack(side="left", padx=6)
        ttk.Button(btns, text="Clear", command=self.clear_files).pack(side="left")

        self.listbox = tk.Listbox(f, height=7)
        self.listbox.pack(fill="both", expand=True, pady=6)

        ttk.Label(f, text="Caption (Reel/Post)").pack(anchor="w")
        self.caption = tk.Text(f, height=4)
        self.caption.pack(fill="x")

        self.upload_btn = ttk.Button(f, text="Upload", command=self.do_upload)
        self.upload_btn.pack(pady=8)
        self.progress = ttk.Progressbar(f, mode="determinate")
        self.progress.pack(fill="x")
        self.status_up = tk.StringVar()
        ttk.Label(f, textvariable=self.status_up, wraplength=500).pack(pady=4)
        ttk.Button(f, text="Logout", command=self.logout).pack(pady=4)

    def _show_upload(self):
        self.login_frame.pack_forget()
        self.who.set(f"Logged in as @{self.username}")
        self.upload_frame.pack(fill="both", expand=True)

    def pick_files(self):
        paths = filedialog.askopenfilenames(
            filetypes=[("Media", "*.jpg *.jpeg *.png *.mp4 *.mov"), ("All", "*")]
        )
        for p in paths:
            if p not in self.files:
                self.files.append(p)
                self.listbox.insert("end", os.path.basename(p))

    def pick_cover(self):
        p = filedialog.askopenfilename(filetypes=[("Image", "*.jpg *.jpeg *.png")])
        if p:
            self.cover = p
            self.status_up.set(f"Cover: {os.path.basename(p)}")

    def clear_files(self):
        self.files.clear()
        self.cover = ""
        self.listbox.delete(0, "end")

    def do_upload(self):
        kind = self.kind.get()
        files = list(self.files)
        caption = self.caption.get("1.0", "end").strip()
        if not files:
            messagebox.showerror("Error", "No files selected.")
            return
        for f in files:
            ext = Path(f).suffix.lower()
            if kind == "Reel" and ext not in VID:
                messagebox.showerror("Error", "Reels need MP4/MOV video.")
                return
            if ext not in IMG + VID:
                messagebox.showerror("Error", f"Unsupported file: {f}")
                return
        self.upload_btn.config(state="disabled")
        self.progress.config(maximum=len(files), value=0)
        self._run(self._upload_thread, kind, files, caption, self.cover)

    def _upload_thread(self, kind, files, caption, cover):
        total = len(files)
        for i, f in enumerate(files, 1):
            self.ui(lambda i=i, f=f: self.status_up.set(f"Uploading {i}/{total}: {os.path.basename(f)} ..."))
            path = Path(f)
            is_vid = path.suffix.lower() in VID
            thumb = Path(cover) if cover else None
            if kind == "Story":
                if is_vid:
                    self.cl.video_upload_to_story(path, thumbnail=thumb)
                else:
                    self.cl.photo_upload_to_story(path)
            elif kind == "Reel":
                self.cl.clip_upload(path, caption, thumbnail=thumb)
            else:  # Post
                if is_vid:
                    self.cl.video_upload(path, caption, thumbnail=thumb)
                else:
                    self.cl.photo_upload(path, caption)
            self.ui(lambda i=i: self.progress.config(value=i))
        self._save_session(self.cl, self.username)
        self.ui(lambda: (self.status_up.set("Upload complete ✔"), self.upload_btn.config(state="normal")))


if __name__ == "__main__":
    App().mainloop()
