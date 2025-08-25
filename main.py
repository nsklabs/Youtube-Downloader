import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import threading
import os
from pathlib import Path
import yt_dlp

# ============================================================
# Default Save Location (Downloads folder)
# ============================================================
DEFAULT_DIR = str(Path.home() / "Downloads")

# ============================================================
# Downloader Class
# ============================================================
class YouTubeDownloader:
    def __init__(self, root):
        self.root = root
        self.root.title("YouTube Video Downloader")
        self.root.geometry("600x400")
        self.root.resizable(False, False)

        # Variables
        self.url_var = tk.StringVar()
        self.format_var = tk.StringVar(value="Video + Audio (MP4)")
        self.resolutions = []
        self.selected_res = tk.StringVar()
        self.download_path = DEFAULT_DIR

        # Progress Variables
        self.progress_var = tk.DoubleVar()
        self.status_var = tk.StringVar(value="Idle")

        self.build_ui()

    # ---------------- UI Layout ----------------
    def build_ui(self):
        frame = ttk.Frame(self.root, padding=15)
        frame.pack(fill="both", expand=True)

        # URL Input
        ttk.Label(frame, text="YouTube URL:").grid(row=0, column=0, sticky="w")
        ttk.Entry(frame, textvariable=self.url_var, width=50).grid(row=0, column=1, padx=5)
        ttk.Button(frame, text="Search", command=self.fetch_formats).grid(row=0, column=2, padx=5)

        # Format Options
        ttk.Label(frame, text="Download Type:").grid(row=1, column=0, sticky="w", pady=10)
        format_menu = ttk.Combobox(frame, textvariable=self.format_var, values=[
            "Video + Audio (MP4)",
            "Audio Only (MP3)",
            "Video Only"
        ], state="readonly", width=30)
        format_menu.grid(row=1, column=1, columnspan=2, sticky="w")

        # Resolution Options
        ttk.Label(frame, text="Available Resolutions:").grid(row=2, column=0, sticky="w")
        self.res_menu = ttk.Combobox(frame, textvariable=self.selected_res, state="disabled", width=30)
        self.res_menu.grid(row=2, column=1, columnspan=2, sticky="w")

        # Buttons
        ttk.Button(frame, text="Browse Folder", command=self.browse_folder).grid(row=3, column=0, pady=10)
        ttk.Button(frame, text="Download", command=self.confirm_download).grid(row=3, column=1, pady=10)

        # Progress Bar
        self.progress_bar = ttk.Progressbar(frame, variable=self.progress_var, maximum=100)
        self.progress_bar.grid(row=4, column=0, columnspan=3, sticky="ew", pady=15)

        # Status Label
        ttk.Label(frame, textvariable=self.status_var, foreground="blue").grid(row=5, column=0, columnspan=3)

    # ---------------- Browse Folder ----------------
    def browse_folder(self):
        folder = filedialog.askdirectory()
        if folder:
            self.download_path = folder

    # ---------------- Fetch Formats ----------------
    def fetch_formats(self):
        url = self.url_var.get().strip()
        if not url:
            messagebox.showerror("Error", "Please enter a YouTube URL!")
            return

        self.status_var.set("Fetching formats...")

        def run():
            try:
                ydl_opts = {"quiet": True, "skip_download": True}
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=False)
                    formats = info.get("formats", [])
                    self.resolutions = [f"{f['format_id']} - {f.get('ext', '')} - {f.get('height', 'Audio')}p"
                                        for f in formats if f.get("ext") in ["mp4", "m4a", "webm"]]

                    if not self.resolutions:
                        self.status_var.set("No formats available!")
                        return

                    self.res_menu.config(state="readonly", values=self.resolutions)
                    self.selected_res.set(self.resolutions[0])
                    self.res_menu.config(state="readonly")
                    self.status_var.set("Formats loaded successfully!")

            except Exception as e:
                messagebox.showerror("Error", f"Failed to fetch formats: {e}")
                self.status_var.set("Error fetching formats!")

        threading.Thread(target=run).start()

    # ---------------- Confirm Download ----------------
    def confirm_download(self):
        if not self.selected_res.get() and self.format_var.get() != "Audio Only (MP3)":
            messagebox.showerror("Error", "Please select a resolution!")
            return

        confirm = messagebox.askokcancel(
            "Confirm Download",
            f"Download Format: {self.format_var.get()}\nResolution: {self.selected_res.get()}\nSave to: {self.download_path}"
        )
        if confirm:
            threading.Thread(target=self.start_download).start()

    # ---------------- Download ----------------
    def start_download(self):
        url = self.url_var.get().strip()
        if not url:
            return

        self.status_var.set("Starting download...")

        def progress_hook(d):
            if d['status'] == 'downloading':
                total = d.get('total_bytes') or d.get('total_bytes_estimate') or 0
                downloaded = d.get('downloaded_bytes', 0)
                speed = d.get('speed') or 0

                percent = (downloaded / total) * 100 if total else 0

                self.progress_var.set(percent)
                self.status_var.set(
                    f"{percent:.1f}% | {downloaded/1024/1024:.2f} MB / "
                    f"{(total/1024/1024):.2f} MB | {speed/1024:.2f} KB/s"
                )

            elif d['status'] == 'finished':
                self.status_var.set("Download complete!")
                self.progress_var.set(100)

        # Default options
        ydl_opts = {
            'outtmpl': os.path.join(self.download_path, '%(title)s.%(ext)s'),
            'progress_hooks': [progress_hook],
            'merge_output_format': 'mp4',   # always output as MP4 if merging
            'postprocessors': []
        }

        # Video + Audio (force single MP4 with sound)
        if self.format_var.get() == "Video + Audio (MP4)":
            ydl_opts['format'] = 'bestvideo+bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegVideoConvertor',
                'preferedformat': 'mp4'
            }]

        # Audio only (MP3)
        elif self.format_var.get() == "Audio Only (MP3)":
            ydl_opts['format'] = 'bestaudio/best'
            ydl_opts['postprocessors'] = [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }]

        # Video only (no audio)
        elif self.format_var.get() == "Video Only":
            ydl_opts['format'] = self.selected_res.get().split(" ")[0]

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                ydl.download([url])
        except Exception as e:
            messagebox.showerror("Error", f"Download failed: {e}")
            self.status_var.set("Download failed!")

# ============================================================
# Run App
# ============================================================
if __name__ == "__main__":
    root = tk.Tk()
    app = YouTubeDownloader(root)
    root.mainloop()
