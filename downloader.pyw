# -*- coding: utf-8 -*-
"""
Universal Media Downloader - Powered by MM
Portativ: yt-dlp.exe və ffmpeg.exe bu faylla eyni qovluqda olmalıdır.
"""

import os
import re
import sys
import queue
import shutil
import ctypes
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, filedialog, messagebox

# ---------------------------------------------------------------- High-DPI
if os.name == "nt":
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
    except Exception:
        try:
            ctypes.windll.user32.SetProcessDPIAware()
        except Exception:
            pass

# ---------------------------------------------------------------- Yollar
if getattr(sys, "frozen", False):
    BASE_DIR = os.path.dirname(os.path.abspath(sys.executable))
else:
    BASE_DIR = os.path.dirname(os.path.abspath(__file__))

CREATE_NO_WINDOW = 0x08000000 if os.name == "nt" else 0


def find_tool(name):
    """Əvvəlcə proqram qovluğunda, tapılmasa sistem PATH-da axtarır."""
    local = os.path.join(BASE_DIR, name + (".exe" if os.name == "nt" else ""))
    if os.path.isfile(local):
        return local
    return shutil.which(name)


# ---------------------------------------------------------------- Rənglər
BG = "#f8fafc"
CARD = "#ffffff"
PRIMARY = "#2563eb"
PRIMARY_HOVER = "#1d4ed8"
PRIMARY_DISABLED = "#93c5fd"
DANGER = "#dc2626"
DANGER_HOVER = "#b91c1c"
TEXT = "#0f172a"
MUTED = "#64748b"
BORDER = "#e2e8f0"
FONT = "Segoe UI"

QUALITIES = {
    "MP3": ["320k", "256k", "128k"],
    "MP4": ["1080p", "720p", "360p"],
}


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Universal Media Downloader")
        self.configure(bg=BG)
        self.resizable(False, False)

        self.msg_queue = queue.Queue()
        self.proc = None
        self.worker = None
        self.cancelled = False
        self.running = False

        self.url_var = tk.StringVar()
        self.fmt_var = tk.StringVar(value="MP4")
        self.quality_var = tk.StringVar()
        self.folder_var = tk.StringVar(value=self._default_folder())
        self.status_var = tk.StringVar(value="Hazırdır.")

        self._setup_window()
        self._setup_styles()
        self._build_ui()
        self._on_format_change()
        self._check_tools()

        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.after(100, self._poll_queue)

    # ------------------------------------------------------------ Pəncərə
    def _setup_window(self):
        scale = self.winfo_fpixels("1i") / 96.0
        w, h = int(600 * scale), int(520 * scale)
        x = (self.winfo_screenwidth() - w) // 2
        y = (self.winfo_screenheight() - h) // 2
        self.geometry(f"{w}x{h}+{x}+{y}")

    def _setup_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure("TFrame", background=BG)
        s.configure("Card.TFrame", background=CARD, relief="solid",
                    borderwidth=1, bordercolor=BORDER)
        s.configure("TLabel", background=BG, foreground=TEXT, font=(FONT, 10))
        s.configure("Card.TLabel", background=CARD, foreground=TEXT, font=(FONT, 10))
        s.configure("Title.TLabel", background=BG, foreground=TEXT, font=(FONT, 18, "bold"))
        s.configure("Sub.TLabel", background=BG, foreground=MUTED, font=(FONT, 10))
        s.configure("Status.TLabel", background=CARD, foreground=MUTED, font=(FONT, 9))
        s.configure("Footer.TLabel", background=BG, foreground=MUTED, font=(FONT, 9))

        s.configure("TEntry", fieldbackground="#ffffff", foreground=TEXT,
                    bordercolor=BORDER, lightcolor=BORDER, darkcolor=BORDER,
                    padding=6, font=(FONT, 10))
        s.map("TEntry", bordercolor=[("focus", PRIMARY)],
              lightcolor=[("focus", PRIMARY)], darkcolor=[("focus", PRIMARY)])

        s.configure("TCombobox", fieldbackground="#ffffff", background="#ffffff",
                    foreground=TEXT, bordercolor=BORDER, arrowcolor=MUTED,
                    padding=5, font=(FONT, 10))
        s.map("TCombobox", fieldbackground=[("readonly", "#ffffff")],
              bordercolor=[("focus", PRIMARY)])
        self.option_add("*TCombobox*Listbox.font", (FONT, 10))

        s.configure("TRadiobutton", background=CARD, foreground=TEXT, font=(FONT, 10))
        s.map("TRadiobutton", background=[("active", CARD)],
              foreground=[("active", PRIMARY)])

        s.configure("Primary.TButton", background=PRIMARY, foreground="#ffffff",
                    font=(FONT, 11, "bold"), padding=(12, 9), borderwidth=0,
                    focusthickness=0, focuscolor=PRIMARY)
        s.map("Primary.TButton",
              background=[("disabled", PRIMARY_DISABLED), ("active", PRIMARY_HOVER)],
              foreground=[("disabled", "#ffffff")])

        s.configure("Danger.TButton", background=DANGER, foreground="#ffffff",
                    font=(FONT, 11, "bold"), padding=(12, 9), borderwidth=0,
                    focusthickness=0, focuscolor=DANGER)
        s.map("Danger.TButton",
              background=[("disabled", "#fca5a5"), ("active", DANGER_HOVER)],
              foreground=[("disabled", "#ffffff")])

        s.configure("Secondary.TButton", background="#e2e8f0", foreground=TEXT,
                    font=(FONT, 10), padding=(12, 6), borderwidth=0,
                    focusthickness=0, focuscolor="#e2e8f0")
        s.map("Secondary.TButton", background=[("active", "#cbd5e1"),
                                               ("disabled", "#f1f5f9")])

        s.configure("Blue.Horizontal.TProgressbar", troughcolor="#e2e8f0",
                    background=PRIMARY, bordercolor="#e2e8f0",
                    lightcolor=PRIMARY, darkcolor=PRIMARY, thickness=12)

    # ------------------------------------------------------------ İnterfeys
    def _build_ui(self):
        outer = ttk.Frame(self, padding=(24, 18, 24, 8))
        outer.pack(fill="both", expand=True)

        ttk.Label(outer, text="Universal Media Downloader",
                  style="Title.TLabel").pack(anchor="w")
        ttk.Label(outer, text="Video və audio faylları sürətlə və rahat yüklə.",
                  style="Sub.TLabel").pack(anchor="w", pady=(0, 12))

        card = ttk.Frame(outer, style="Card.TFrame", padding=16)
        card.pack(fill="x")
        card.columnconfigure(0, weight=1)

        # URL
        ttk.Label(card, text="Video / Audio linki", style="Card.TLabel").grid(
            row=0, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.url_entry = ttk.Entry(card, textvariable=self.url_var)
        self.url_entry.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        self.url_entry.focus_set()

        # Format + keyfiyyət
        opts = ttk.Frame(card, style="Card.TFrame")
        opts.configure(borderwidth=0)
        opts.grid(row=2, column=0, columnspan=2, sticky="ew", pady=(0, 12))
        opts.columnconfigure(2, weight=1)

        ttk.Label(opts, text="Format", style="Card.TLabel").grid(
            row=0, column=0, sticky="w", columnspan=2)
        ttk.Radiobutton(opts, text="MP4 (Video)", value="MP4",
                        variable=self.fmt_var,
                        command=self._on_format_change).grid(row=1, column=0, sticky="w")
        ttk.Radiobutton(opts, text="MP3 (Səs)", value="MP3",
                        variable=self.fmt_var,
                        command=self._on_format_change).grid(row=1, column=1,
                                                             sticky="w", padx=(16, 0))

        ttk.Label(opts, text="Keyfiyyət", style="Card.TLabel").grid(
            row=0, column=3, sticky="w", padx=(0, 0))
        self.quality_cb = ttk.Combobox(opts, textvariable=self.quality_var,
                                       state="readonly", width=12)
        self.quality_cb.grid(row=1, column=3, sticky="e")

        # Qovluq
        ttk.Label(card, text="Yadda saxlama qovluğu", style="Card.TLabel").grid(
            row=3, column=0, columnspan=2, sticky="w", pady=(0, 4))
        self.folder_entry = ttk.Entry(card, textvariable=self.folder_var)
        self.folder_entry.grid(row=4, column=0, sticky="ew", padx=(0, 8))
        self.browse_btn = ttk.Button(card, text="Gözat...", style="Secondary.TButton",
                                     command=self._browse)
        self.browse_btn.grid(row=4, column=1)

        # Düymələr
        btns = ttk.Frame(outer)
        btns.pack(fill="x", pady=(14, 10))
        btns.columnconfigure(0, weight=1)
        self.start_btn = ttk.Button(btns, text="Endirməyə Başla",
                                    style="Primary.TButton", command=self._start)
        self.start_btn.grid(row=0, column=0, sticky="ew")
        self.cancel_btn = ttk.Button(btns, text="Ləğv et", style="Danger.TButton",
                                     command=self._cancel, state="disabled")
        self.cancel_btn.grid(row=0, column=1, padx=(8, 0))

        # Progress
        prog = ttk.Frame(outer, style="Card.TFrame", padding=14)
        prog.pack(fill="x")
        self.progress = ttk.Progressbar(prog, style="Blue.Horizontal.TProgressbar",
                                        mode="determinate", maximum=100)
        self.progress.pack(fill="x")
        self.status_lbl = ttk.Label(prog, textvariable=self.status_var,
                                    style="Status.TLabel", wraplength=500,
                                    justify="left")
        self.status_lbl.pack(anchor="w", pady=(8, 0))

        # Footer
        ttk.Label(self, text="Powered by MM", style="Footer.TLabel").pack(
            side="bottom", pady=(0, 10))

    # ------------------------------------------------------------ Köməkçilər
    @staticmethod
    def _default_folder():
        home = os.path.expanduser("~")
        dl = os.path.join(home, "Downloads")
        return dl if os.path.isdir(dl) else home

    def _check_tools(self):
        missing = []
        if not find_tool("yt-dlp"):
            missing.append("yt-dlp.exe")
        if not find_tool("ffmpeg"):
            missing.append("ffmpeg.exe")
        if missing:
            self.status_var.set("Diqqət: " + ", ".join(missing) +
                                " tapılmadı. Faylları proqramın qovluğuna qoyun.")

    def _on_format_change(self):
        values = QUALITIES[self.fmt_var.get()]
        self.quality_cb["values"] = values
        self.quality_var.set(values[0])

    def _browse(self):
        folder = filedialog.askdirectory(initialdir=self.folder_var.get() or None,
                                         title="Qovluq seçin")
        if folder:
            self.folder_var.set(os.path.normpath(folder))

    def _set_busy(self, busy):
        self.running = busy
        state = "disabled" if busy else "normal"
        self.start_btn.configure(state=state)
        self.browse_btn.configure(state=state)
        self.url_entry.configure(state=state)
        self.folder_entry.configure(state=state)
        self.quality_cb.configure(state="disabled" if busy else "readonly")
        self.cancel_btn.configure(state="normal" if busy else "disabled")

    def _set_progress_mode(self, indeterminate):
        if indeterminate:
            self.progress.configure(mode="indeterminate")
            self.progress.start(12)
        else:
            self.progress.stop()
            self.progress.configure(mode="determinate")

    # ------------------------------------------------------------ Əmr qurulması
    def _build_command(self, ytdlp, ffmpeg, url, folder, fmt, quality):
        cmd = [
            ytdlp,
            "--no-playlist",
            "--newline",
            "--no-colors",
            "--encoding", "utf-8",
            "--windows-filenames",
            "-P", folder,
            "-o", "%(title).150B [%(id)s].%(ext)s",
        ]
        if ffmpeg:
            cmd += ["--ffmpeg-location", os.path.dirname(ffmpeg)]

        if fmt == "MP3":
            cmd += ["-f", "bestaudio/best",
                    "-x", "--audio-format", "mp3",
                    "--audio-quality", quality.upper()]
        else:
            h = quality.replace("p", "")
            cmd += ["-f", f"bv*[height<={h}]+ba/b[height<={h}]/bv*+ba/b",
                    "--merge-output-format", "mp4"]

        cmd.append(url)
        return cmd

    # ------------------------------------------------------------ Başlat / Ləğv
    def _start(self):
        if self.running:
            return

        url = self.url_var.get().strip()
        folder = self.folder_var.get().strip()
        fmt = self.fmt_var.get()
        quality = self.quality_var.get()

        if not url or not re.match(r"^https?://", url, re.I):
            messagebox.showwarning("Link səhvdir",
                                   "Zəhmət olmasa düzgün link daxil edin\n"
                                   "(http:// və ya https:// ilə başlamalıdır).")
            return

        ytdlp = find_tool("yt-dlp")
        ffmpeg = find_tool("ffmpeg")
        if not ytdlp:
            messagebox.showerror("yt-dlp tapılmadı",
                                 "yt-dlp.exe faylı proqramın qovluğunda tapılmadı:\n\n"
                                 f"{BASE_DIR}\n\nFaylı bu qovluğa yerləşdirin.")
            return
        if not ffmpeg:
            messagebox.showerror("ffmpeg tapılmadı",
                                 "ffmpeg.exe faylı proqramın qovluğunda tapılmadı:\n\n"
                                 f"{BASE_DIR}\n\nFaylı bu qovluğa yerləşdirin.")
            return

        if not folder:
            messagebox.showwarning("Qovluq seçilməyib",
                                   "Zəhmət olmasa yadda saxlama qovluğunu seçin.")
            return
        try:
            os.makedirs(folder, exist_ok=True)
        except Exception as e:
            messagebox.showerror("Qovluq xətası", f"Qovluq yaradıla bilmədi:\n{e}")
            return

        cmd = self._build_command(ytdlp, ffmpeg, url, folder, fmt, quality)

        self.cancelled = False
        self._set_busy(True)
        self._set_progress_mode(False)
        self.progress["value"] = 0
        self.status_var.set("Başlayır... Məlumat alınır.")

        self.worker = threading.Thread(target=self._run_process,
                                       args=(cmd, folder), daemon=True)
        self.worker.start()

    def _cancel(self):
        if not self.running:
            return
        self.cancelled = True
        self.status_var.set("Ləğv edilir...")
        self._kill_process()

    def _kill_process(self):
        p = self.proc
        if p and p.poll() is None:
            try:
                if os.name == "nt":
                    subprocess.run(["taskkill", "/F", "/T", "/PID", str(p.pid)],
                                   creationflags=CREATE_NO_WINDOW,
                                   stdout=subprocess.DEVNULL,
                                   stderr=subprocess.DEVNULL)
                else:
                    p.terminate()
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass

    # ------------------------------------------------------------ Arxa fon işçisi
    def _run_process(self, cmd, folder):
        q = self.msg_queue
        errors = []
        dest_count = 0
        pct_re = re.compile(r"\[download\]\s+(\d+(?:\.\d+)?)%")
        speed_re = re.compile(r"at\s+(\S+)\s+ETA\s+(\S+)")

        try:
            self.proc = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                stdin=subprocess.DEVNULL,
                text=True,
                encoding="utf-8",
                errors="replace",
                creationflags=CREATE_NO_WINDOW,
                cwd=BASE_DIR,
            )

            for raw in self.proc.stdout:
                line = raw.strip()
                if not line:
                    continue

                if line.startswith("ERROR"):
                    errors.append(line)
                    continue

                m = pct_re.search(line)
                if m:
                    pct = float(m.group(1))
                    extra = ""
                    sm = speed_re.search(line)
                    if sm:
                        extra = f"  •  {sm.group(1)}  •  qalan: {sm.group(2)}"
                    part = f" (hissə {dest_count})" if dest_count > 1 else ""
                    q.put(("progress", pct,
                           f"Yüklənir{part}: {pct:.1f}%{extra}"))
                    continue

                if line.startswith("[download] Destination:"):
                    dest_count += 1
                    q.put(("status", "Fayl yüklənməyə hazırlanır..."))
                elif line.startswith("[Merger]"):
                    q.put(("busy", "Video və səs ffmpeg ilə tək fayla birləşdirilir..."))
                elif line.startswith("[ExtractAudio]"):
                    q.put(("busy", "ffmpeg ilə MP3 formatına çevrilir..."))
                elif line.startswith("[info]") or line.startswith("[youtube]") \
                        or line.startswith("[generic]"):
                    q.put(("status", "Məlumat alınır..."))

            code = self.proc.wait()

            if self.cancelled:
                q.put(("cancelled",))
            elif code == 0:
                q.put(("done", folder))
            else:
                msg = "\n".join(errors[-4:]) if errors else \
                    f"yt-dlp xəta kodu ilə bitdi: {code}"
                q.put(("error", msg))

        except FileNotFoundError:
            q.put(("error", "yt-dlp işə salına bilmədi. Fayl mövcud deyil."))
        except Exception as e:
            q.put(("error", f"Gözlənilməz xəta:\n{e}"))
        finally:
            self.proc = None

    # ------------------------------------------------------------ Növbəni oxu (UI thread)
    def _poll_queue(self):
        try:
            while True:
                msg = self.msg_queue.get_nowait()
                kind = msg[0]

                if kind == "progress":
                    if str(self.progress.cget("mode")) != "determinate":
                        self._set_progress_mode(False)
                    self.progress["value"] = msg[1]
                    self.status_var.set(msg[2])

                elif kind == "status":
                    self.status_var.set(msg[1])

                elif kind == "busy":
                    self._set_progress_mode(True)
                    self.status_var.set(msg[1])

                elif kind == "done":
                    self._set_progress_mode(False)
                    self.progress["value"] = 100
                    self.status_var.set("Tamamlandı! Fayl uğurla yüklənib.")
                    self._set_busy(False)
                    if messagebox.askyesno("Uğurlu",
                                           "Yükləmə uğurla tamamlandı.\n\n"
                                           "Qovluğu açmaq istəyirsiniz?"):
                        self._open_folder(msg[1])

                elif kind == "cancelled":
                    self._set_progress_mode(False)
                    self.progress["value"] = 0
                    self.status_var.set("Yükləmə ləğv edildi.")
                    self._set_busy(False)

                elif kind == "error":
                    self._set_progress_mode(False)
                    self.progress["value"] = 0
                    self.status_var.set("Xəta baş verdi.")
                    self._set_busy(False)
                    messagebox.showerror("Yükləmə xətası", msg[1])

        except queue.Empty:
            pass
        self.after(100, self._poll_queue)

    @staticmethod
    def _open_folder(path):
        try:
            if os.name == "nt":
                os.startfile(path)
            elif sys.platform == "darwin":
                subprocess.Popen(["open", path])
            else:
                subprocess.Popen(["xdg-open", path])
        except Exception as e:
            messagebox.showerror("Xəta", f"Qovluq açıla bilmədi:\n{e}")

    def _on_close(self):
        if self.running:
            if not messagebox.askyesno("Çıxış",
                                       "Yükləmə davam edir. Çıxmaq istəyirsiniz?"):
                return
            self.cancelled = True
            self._kill_process()
        self.destroy()


if __name__ == "__main__":
    App().mainloop()