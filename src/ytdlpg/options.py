import os


# Default download path
default_download_path = os.path.join(os.path.expanduser("~"), "Downloads")


class YtdlpOptions:
    def __init__(self):
        self.format = "best"
        self.output_path = default_download_path
        self.extract_audio = False
        self.audio_format = "mp3"
        self.audio_quality = "0"  # Best quality
        self.playlist = False
        self.subtitles = False
        self.subtitle_lang = "en"
        self.thumbnail = False
        self.verbose = False

    def to_ydl_opts(self):
        opts = {
            "format": self.format,
            "outtmpl": os.path.join(self.output_path, "%(title)s.%(ext)s"),
            "verbose": self.verbose,
        }

        if self.extract_audio:
            opts["postprocessors"] = [
                {
                    "key": "FFmpegExtractAudio",
                    "preferredcodec": self.audio_format,
                    "preferredquality": self.audio_quality,
                }
            ]
            opts["format"] = "bestaudio/best"

        if self.subtitles:
            opts["writesubtitles"] = True
            opts["subtitleslangs"] = [self.subtitle_lang]

        if self.thumbnail:
            opts["writethumbnail"] = True
            if "postprocessors" not in opts:
                opts["postprocessors"] = []
            opts["postprocessors"].append({"key": "EmbedThumbnail"})

        return opts
