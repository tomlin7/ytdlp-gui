import json
import os
import platform
import tempfile
from datetime import datetime

from ytdlpg.options import default_download_path
from ytdlpg.manager import DownloadManager

import flet as ft
import yt_dlp


def main(page: ft.Page):
    page.title = "YT-DLP GUI"
    page.theme_mode = ft.ThemeMode.DARK
    page.window.width = 1200
    page.window.height = 800
    page.window.min_width = 800
    page.window.min_height = 600
    page.scroll = ft.ScrollMode.AUTO
    page.padding = 20

    download_manager = DownloadManager(page)

    url_field = ft.TextField(
        label="Enter YouTube URL",
        autofocus=True,
        expand=True,
        border_color=ft.Colors.BLUE_400,
        focused_border_color=ft.Colors.BLUE_ACCENT,
        hint_text="https://www.youtube.com/watch?v=...",
    )

    active_downloads = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    download_history = ft.Column(spacing=10, scroll=ft.ScrollMode.AUTO)

    status_text = ft.Text("Ready to download", color=ft.Colors.GREEN)

    stats_row = ft.Row(
        [ft.Text("Total Downloads: 0"), ft.Text("Completed: 0"), ft.Text("Failed: 0")],
        alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
    )

    def update_stats():
        completed = len(
            [
                d
                for d in download_manager.downloads_history
                if d["status"] == "completed"
            ]
        )
        failed = len(
            [d for d in download_manager.downloads_history if d["status"] == "error"]
        )
        total = len(download_manager.current_downloads) + len(
            download_manager.downloads_history
        )

        stats_row.controls[0].value = f"Total Downloads: {total}"
        stats_row.controls[1].value = f"Completed: {completed}"
        stats_row.controls[2].value = f"Failed: {failed}"
        page.update()

    def on_progress(download_info):
        def find_download_card():
            for control in active_downloads.controls:
                if control.data == download_info["url"]:
                    return control
            return None

        card = find_download_card()
        if card:
            progress_bar = card.content.content.controls[1]
            info_text = card.content.content.controls[2]

            progress_bar.value = download_info["progress"] / 100
            status = download_info["status"]
            speed_str = (
                f" - {format_size(download_info.get('speed', 0))}/s"
                if "speed" in download_info
                else ""
            )
            info_text.value = (
                f"{download_info['title']} - {status.capitalize()}{speed_str}"
            )
            page.update()

    def on_complete(download_info):
        def find_download_card():
            for control in active_downloads.controls:
                if control.data == download_info["url"]:
                    return control
            return None

        card = find_download_card()
        if card:
            active_downloads.controls.remove(card)

            history_card = create_history_card(download_info)
            download_history.controls.insert(0, history_card)

            status_text.value = f"Download completed: {download_info['title']}"
            status_text.color = ft.Colors.GREEN
            update_stats()
            page.update()

    def on_error(download_info, error_message):
        def find_download_card():
            for control in active_downloads.controls:
                if control.data == download_info["url"]:
                    return control
            return None

        card = find_download_card()
        if card:
            active_downloads.controls.remove(card)

            history_card = create_history_card(download_info)
            download_history.controls.insert(0, history_card)

            status_text.value = f"Download failed: {error_message}"
            status_text.color = ft.Colors.RED
            update_stats()
            page.update()

    def create_download_card(download_info):
        progress = ft.ProgressBar(width=800, value=0, color=ft.Colors.BLUE)
        info_text = ft.Text(
            f"{download_info['title']} - {download_info['status'].capitalize()}",
            size=14,
        )

        cancel_btn = ft.IconButton(
            icon=ft.Icons.CANCEL_OUTLINED,
            icon_color=ft.Colors.RED_400,
            tooltip="Cancel download",
            on_click=lambda e: cancel_download(download_info),
        )

        card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                ft.Icon(ft.Icons.DOWNLOADING, color=ft.Colors.BLUE),
                                ft.Text(
                                    download_info["url"],
                                    size=14,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                                cancel_btn,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        progress,
                        info_text,
                    ],
                    spacing=10,
                ),
                padding=15,
            ),
            data=download_info["url"],
        )
        return card

    def create_history_card(download_info):
        if download_info["status"] == "completed":
            icon = ft.Icon(ft.Icons.CHECK_CIRCLE, color=ft.Colors.GREEN)
            status_color = ft.Colors.GREEN
        else:
            icon = ft.Icon(ft.Icons.ERROR, color=ft.Colors.RED)
            status_color = ft.Colors.RED

        duration = ""
        if "start_time" in download_info and "end_time" in download_info:
            delta = download_info["end_time"] - download_info["start_time"]
            duration = f" ({delta.seconds}s)"

        open_folder_btn = ft.IconButton(
            icon=ft.Icons.FOLDER_OPEN,
            tooltip="Open folder",
            on_click=lambda e: open_download_folder(download_info["path"]),
        )

        card = ft.Card(
            content=ft.Container(
                content=ft.Column(
                    [
                        ft.Row(
                            [
                                icon,
                                ft.Text(
                                    download_info["title"],
                                    size=16,
                                    weight=ft.FontWeight.BOLD,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ],
                            alignment=ft.MainAxisAlignment.START,
                        ),
                        ft.Row(
                            [
                                ft.Text(
                                    download_info["url"],
                                    size=12,
                                    overflow=ft.TextOverflow.ELLIPSIS,
                                ),
                            ]
                        ),
                        ft.Row(
                            [
                                ft.Text(
                                    f"Status: {download_info['status'].capitalize()}{duration}",
                                    color=status_color,
                                ),
                                open_folder_btn,
                            ],
                            alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                        ),
                        ft.Text(download_info.get("error", ""), color=ft.Colors.RED)
                        if "error" in download_info
                        else ft.Container(),
                    ],
                    spacing=5,
                ),
                padding=15,
            ),
            data=download_info["url"],
        )
        return card

    def open_download_folder(path):
        if os.path.exists(path):
            if platform.system() == "Windows":
                os.startfile(path)
            elif platform.system() == "Darwin":
                os.system(f'open "{path}"')
            else:
                os.system(f'xdg-open "{path}"')

    def format_size(bytes_size):
        try:
            if bytes_size < 1024:
                return f"{bytes_size} B"
            elif bytes_size < 1024 * 1024:
                return f"{bytes_size / 1024:.1f} KB"
            elif bytes_size < 1024 * 1024 * 1024:
                return f"{bytes_size / (1024 * 1024):.1f} MB"
            else:
                return f"{bytes_size / (1024 * 1024 * 1024):.1f} GB"
        except Exception:
            return "Unknown"

    def cancel_download(download_info):
        for control in active_downloads.controls[:]:
            if control.data == download_info["url"]:
                active_downloads.controls.remove(control)

                download_info["status"] = "cancelled"
                download_info["end_time"] = datetime.now()

                history_card = create_history_card(download_info)
                download_history.controls.insert(0, history_card)

                status_text.value = f"Download cancelled: {download_info['title']}"
                status_text.color = ft.Colors.ORANGE
                update_stats()
                page.update()
                break

    format_dropdown = ft.Dropdown(
        width=200,
        label="Video Format",
        options=[
            ft.dropdown.Option("best", "Best Quality"),
            ft.dropdown.Option("bestvideo+bestaudio", "Best Video + Audio"),
            ft.dropdown.Option("136+140", "720p + Audio"),
            ft.dropdown.Option("135+140", "480p + Audio"),
            ft.dropdown.Option("134+140", "360p + Audio"),
        ],
        value="best",
    )

    extract_audio_switch = ft.Switch(label="Extract Audio", value=False)

    audio_format_dropdown = ft.Dropdown(
        width=100,
        label="Audio Format",
        options=[
            ft.dropdown.Option("mp3", "MP3"),
            ft.dropdown.Option("m4a", "M4A"),
            ft.dropdown.Option("wav", "WAV"),
            ft.dropdown.Option("flac", "FLAC"),
        ],
        value="mp3",
        disabled=not extract_audio_switch.value,
    )

    audio_quality_dropdown = ft.Dropdown(
        width=100,
        label="Audio Quality",
        options=[
            ft.dropdown.Option("0", "Best"),
            ft.dropdown.Option("5", "Medium"),
            ft.dropdown.Option("9", "Low"),
        ],
        value="0",
        disabled=not extract_audio_switch.value,
    )

    def on_extract_audio_change(e):
        audio_format_dropdown.disabled = not extract_audio_switch.value
        audio_quality_dropdown.disabled = not extract_audio_switch.value
        page.update()

    extract_audio_switch.on_change = on_extract_audio_change

    output_path_field = ft.TextField(
        label="Output Directory",
        value=default_download_path,
        expand=True,
        read_only=True,
    )

    def pick_directory(e):
        def on_dialog_result(e):
            if e.data:
                output_path_field.value = e.data
                download_manager.options.output_path = e.data
                page.update()

        page.launch_file_picker(
            on_result=on_dialog_result,
            directory=True,
            initial_directory=download_manager.options.output_path,
        )

    playlist_switch = ft.Switch(label="Download Playlist", value=False)
    subtitles_switch = ft.Switch(label="Download Subtitles", value=False)
    thumbnail_switch = ft.Switch(label="Download Thumbnail", value=False)

    subtitle_lang_dropdown = ft.Dropdown(
        width=100,
        label="Subtitle Language",
        options=[
            ft.dropdown.Option("en", "English"),
            ft.dropdown.Option("fr", "French"),
            ft.dropdown.Option("es", "Spanish"),
            ft.dropdown.Option("de", "German"),
            ft.dropdown.Option("it", "Italian"),
            ft.dropdown.Option("ja", "Japanese"),
        ],
        value="en",
        disabled=not subtitles_switch.value,
    )

    def on_subtitles_change(e):
        subtitle_lang_dropdown.disabled = not subtitles_switch.value
        page.update()

    subtitles_switch.on_change = on_subtitles_change

    verbose_switch = ft.Switch(label="Verbose Output", value=False)

    def update_options():
        download_manager.options.format = format_dropdown.value
        download_manager.options.output_path = output_path_field.value
        download_manager.options.extract_audio = extract_audio_switch.value
        download_manager.options.audio_format = audio_format_dropdown.value
        download_manager.options.audio_quality = audio_quality_dropdown.value
        download_manager.options.playlist = playlist_switch.value
        download_manager.options.subtitles = subtitles_switch.value
        download_manager.options.subtitle_lang = subtitle_lang_dropdown.value
        download_manager.options.thumbnail = thumbnail_switch.value
        download_manager.options.verbose = verbose_switch.value

    def start_download(e):
        url = url_field.value.strip()
        if not url:
            status_text.value = "Please enter a valid URL"
            status_text.color = ft.Colors.RED
            page.update()
            return

        update_options()

        download_info = {
            "url": url,
            "start_time": datetime.now(),
            "status": "initializing",
            "progress": 0,
            "title": "Initializing...",
            "path": download_manager.options.output_path,
        }

        download_card = create_download_card(download_info)
        active_downloads.controls.append(download_card)

        url_field.value = ""

        status_text.value = "Starting download..."
        status_text.color = ft.Colors.BLUE
        update_stats()
        page.update()

        download_manager.download(url, on_progress, on_complete, on_error)

    download_button = ft.ElevatedButton(
        text="Download",
        icon=ft.Icons.DOWNLOAD,
        on_click=start_download,
        bgcolor=ft.Colors.BLUE,
        color=ft.Colors.WHITE,
        height=50,
    )

    def paste_from_clipboard(e):
        page.set_clipboard("")
        page.get_clipboard(on_clipboard_data)

    def on_clipboard_data(e):
        if e.data and isinstance(e.data, str):
            url_field.value = e.data
            page.update()

    paste_button = ft.IconButton(
        icon=ft.Icons.PASTE,
        tooltip="Paste from clipboard",
        on_click=paste_from_clipboard,
    )

    def clear_url(e):
        url_field.value = ""
        page.update()

    clear_button = ft.IconButton(
        icon=ft.Icons.CLEAR,
        tooltip="Clear",
        on_click=clear_url,
    )

    def export_settings(e):
        settings = vars(download_manager.options)
        fd = tempfile.NamedTemporaryFile(delete=False, suffix=".json")
        with open(fd.name, "w") as f:
            json.dump(settings, f, indent=2)

        status_text.value = f"Settings exported to {fd.name}"
        status_text.color = ft.Colors.GREEN
        page.update()

    export_settings_button = ft.TextButton(
        text="Export Settings",
        icon=ft.Icons.DOWNLOAD_FOR_OFFLINE,
        on_click=export_settings,
    )

    def import_settings(e):
        def on_dialog_result(e):
            if e.data:
                file_path = e.data[0]
                try:
                    with open(file_path, "r") as f:
                        settings = json.load(f)

                    for key, value in settings.items():
                        if hasattr(download_manager.options, key):
                            setattr(download_manager.options, key, value)

                    format_dropdown.value = download_manager.options.format
                    output_path_field.value = download_manager.options.output_path
                    extract_audio_switch.value = download_manager.options.extract_audio
                    audio_format_dropdown.value = download_manager.options.audio_format
                    audio_quality_dropdown.value = (
                        download_manager.options.audio_quality
                    )
                    playlist_switch.value = download_manager.options.playlist
                    subtitles_switch.value = download_manager.options.subtitles
                    subtitle_lang_dropdown.value = (
                        download_manager.options.subtitle_lang
                    )
                    thumbnail_switch.value = download_manager.options.thumbnail
                    verbose_switch.value = download_manager.options.verbose

                    audio_format_dropdown.disabled = not extract_audio_switch.value
                    audio_quality_dropdown.disabled = not extract_audio_switch.value
                    subtitle_lang_dropdown.disabled = not subtitles_switch.value

                    status_text.value = "Settings imported successfully"
                    status_text.color = ft.Colors.GREEN
                    page.update()
                except Exception as e:
                    status_text.value = f"Error importing settings: {str(e)}"
                    status_text.color = ft.Colors.RED
                    page.update()

        page.launch_file_picker(
            on_result=on_dialog_result,
            allowed_extensions=["json"],
            file_type=ft.FilePickerFileType.CUSTOM,
            allow_multiple=False,
        )

    import_settings_button = ft.TextButton(
        text="Import Settings",
        icon=ft.Icons.UPLOAD_FILE,
        on_click=import_settings,
    )

    def show_about(e):
        page.open(about_dialog)

    def highlight_link(e):
        e.control.style.color = ft.Colors.BLUE
        e.control.update()

    def unhighlight_link(e):
        e.control.style.color = None
        e.control.update()

    about_dialog = ft.AlertDialog(
        title=ft.Text("About YT-DLP GUI"),
        content=ft.Column(
            [
                ft.Text("A beautiful GUI for YT-DLP."),
                ft.Text(
                    spans=[
                        ft.TextSpan(
                            "Made with ❤️ by @Tomlin7",
                            ft.TextStyle(decoration=ft.TextDecoration.UNDERLINE),
                            url="https://github.com/tomlin7",
                            on_enter=highlight_link,
                            on_exit=unhighlight_link,
                        )
                    ]
                ),
                ft.Text("Version 1.0.0"),
                ft.Text("yt-dlp version: " + yt_dlp.version.__version__),
            ],
            tight=True,
        ),
        actions=[
            ft.TextButton("Close", on_click=lambda e: close_dialog(about_dialog)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def show_help(e):
        page.open(help_dialog)

    help_dialog = ft.AlertDialog(
        modal=True,
        title=ft.Text("Help"),
        content=ft.Column(
            [
                ft.Text("How to use YT-DLP GUI:", weight=ft.FontWeight.BOLD),
                ft.Text("1. Enter a YouTube URL in the input field"),
                ft.Text("2. Configure download options if needed"),
                ft.Text("3. Click the Download button"),
                ft.Text("4. Monitor progress in the Active Downloads tab"),
                ft.Text("5. View completed downloads in the History tab"),
                ft.Text("\nSupported URLs:", weight=ft.FontWeight.BOLD),
                ft.Text("- YouTube videos and playlists"),
                ft.Text("- Other platforms supported by yt-dlp"),
            ],
            tight=True,
            scroll=ft.ScrollMode.AUTO,
        ),
        actions=[
            ft.TextButton("Close", on_click=lambda e: close_dialog(help_dialog)),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )

    def close_dialog(dialog):
        page.close(dialog)

    browse_button = ft.IconButton(
        icon=ft.Icons.FOLDER_OPEN,
        tooltip="Browse",
        on_click=pick_directory,
    )

    page.add(
        ft.Column(
            [
                ft.Row(
                    [
                        ft.Text(
                            "YT-DLP GUI",
                            size=30,
                            weight=ft.FontWeight.BOLD,
                            color=ft.Colors.RED_500,
                        ),
                        ft.Row(
                            [
                                ft.IconButton(
                                    icon=ft.Icons.HELP_OUTLINE,
                                    tooltip="Help",
                                    on_click=show_help,
                                ),
                                ft.IconButton(
                                    icon=ft.Icons.INFO_OUTLINE,
                                    tooltip="About",
                                    on_click=show_about,
                                ),
                            ]
                        ),
                    ],
                    alignment=ft.MainAxisAlignment.SPACE_BETWEEN,
                ),
                ft.Card(
                    content=ft.Container(
                        content=ft.Column(
                            [
                                ft.Text("Download", size=20, weight=ft.FontWeight.BOLD),
                                ft.Row(
                                    [
                                        url_field,
                                        paste_button,
                                        clear_button,
                                        download_button,
                                    ],
                                    alignment=ft.MainAxisAlignment.CENTER,
                                    vertical_alignment=ft.CrossAxisAlignment.CENTER,
                                ),
                            ],
                            spacing=15,
                        ),
                        padding=20,
                    ),
                    elevation=5,
                ),
                ft.ExpansionTile(
                    title=ft.Text("Download Settings", weight=ft.FontWeight.W_500),
                    subtitle=ft.Text("Configure download options"),
                    leading=ft.Icon(ft.Icons.SETTINGS),
                    controls=[
                        ft.Card(
                            content=ft.Container(
                                content=ft.Column(
                                    [
                                        ft.Text(
                                            "Video and Format",
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Row(
                                            [
                                                format_dropdown,
                                                extract_audio_switch,
                                                audio_format_dropdown,
                                                audio_quality_dropdown,
                                            ],
                                            wrap=True,
                                        ),
                                        ft.Divider(),
                                        ft.Text(
                                            "Output Settings", weight=ft.FontWeight.BOLD
                                        ),
                                        ft.Row(
                                            [
                                                output_path_field,
                                                browse_button,
                                            ]
                                        ),
                                        ft.Divider(),
                                        ft.Text(
                                            "Additional Options",
                                            weight=ft.FontWeight.BOLD,
                                        ),
                                        ft.Row(
                                            [
                                                playlist_switch,
                                                subtitles_switch,
                                                subtitle_lang_dropdown,
                                                thumbnail_switch,
                                                verbose_switch,
                                            ],
                                            wrap=True,
                                        ),
                                        ft.Divider(),
                                        ft.Row(
                                            [
                                                import_settings_button,
                                                export_settings_button,
                                            ],
                                            alignment=ft.MainAxisAlignment.END,
                                        ),
                                    ],
                                    spacing=10,
                                ),
                                padding=20,
                            ),
                        ),
                    ],
                ),
                ft.Container(
                    content=status_text,
                    padding=10,
                    border_radius=5,
                    bgcolor=ft.Colors.SURFACE,
                ),
                ft.Tabs(
                    selected_index=0,
                    animation_duration=300,
                    tabs=[
                        ft.Tab(
                            text="Active Downloads",
                            icon=ft.Icons.DOWNLOADING,
                            content=ft.Container(
                                content=active_downloads,
                                padding=10,
                                height=300,
                            ),
                        ),
                        ft.Tab(
                            text="History",
                            icon=ft.Icons.HISTORY,
                            content=ft.Container(
                                content=download_history,
                                padding=10,
                                height=300,
                            ),
                        ),
                    ],
                    expand=1,
                ),
                stats_row,
            ]
        )
    )


def python_main():
    ft.app(main)


if __name__ == "__main__":
    python_main()
