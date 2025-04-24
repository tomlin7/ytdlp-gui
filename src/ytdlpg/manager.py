import threading
from datetime import datetime

import yt_dlp

from ytdlpg.options import YtdlpOptions


class DownloadManager:
    def __init__(self, page):
        self.page = page
        self.current_downloads = []
        self.downloads_history = []
        self.options = YtdlpOptions()

    def download(self, url, on_progress, on_complete, on_error):
        download_info = {
            "url": url,
            "start_time": datetime.now(),
            "status": "downloading",
            "progress": 0,
            "title": "Fetching...",
            "path": self.options.output_path,
        }
        self.current_downloads.append(download_info)

        def progress_hook(d):
            if d["status"] == "downloading":
                if "total_bytes" in d and d["total_bytes"] > 0:
                    download_info["progress"] = (
                        d["downloaded_bytes"] / d["total_bytes"] * 100
                    )
                elif "total_bytes_estimate" in d and d["total_bytes_estimate"] > 0:
                    download_info["progress"] = (
                        d["downloaded_bytes"] / d["total_bytes_estimate"] * 100
                    )

                download_info["title"] = d.get("info_dict", {}).get("title", "Unknown")
                download_info["speed"] = d.get("speed", 0)

                on_progress(download_info)

            elif d["status"] == "finished":
                download_info["status"] = "processing"
                download_info["title"] = d.get("info_dict", {}).get("title", "Unknown")
                download_info["progress"] = 100
                on_progress(download_info)

        def download_thread():
            try:
                ydl_opts = self.options.to_ydl_opts()
                ydl_opts["progress_hooks"] = [progress_hook]

                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(url, download=True)
                    download_info["title"] = info.get("title", "Unknown")
                    download_info["duration"] = info.get("duration", 0)
                    download_info["status"] = "completed"
                    download_info["end_time"] = datetime.now()

                    self.current_downloads.remove(download_info)
                    self.downloads_history.append(download_info)

                    on_complete(download_info)
            except Exception as e:
                download_info["status"] = "error"
                download_info["error"] = str(e)
                download_info["end_time"] = datetime.now()

                if download_info in self.current_downloads:
                    self.current_downloads.remove(download_info)
                self.downloads_history.append(download_info)

                on_error(download_info, str(e))

        threading.Thread(target=download_thread, daemon=True).start()
