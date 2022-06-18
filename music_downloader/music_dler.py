import json
import re
import subprocess
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Mapping, Optional, Pattern, TypedDict, cast

from progressbar import ProgressBar
from yt_dlp import parse_options
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.utils import DateRange, RejectedVideoReached, match_filter_func
from yt_dlp.YoutubeDL import YoutubeDL

from .crop_covers import crop_edges
from .tagger import tag_folder

MUSIC_PATH = Path().home() / "Musique"
MUSIC_LIST = MUSIC_PATH / "musique.lst"
CONFIG_PATH = Path.home() / ".yt-downloader"
LAST_DLED_CHANNELS = CONFIG_PATH / "last_dled_channels.json"


class MyLogger:
    def debug(self, msg):
        if msg.startswith("[download]"):
            return
        else:
            print(msg)

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)


class DownloadStep(TypedDict):
    status: str
    downloaded_bytes: int
    total_bytes: int
    tmpfilename: str
    filename: str
    eta: int
    speed: float
    elapsed: float
    ctx_id: None
    info_dict: dict
    _eta_str: str
    _percent_str: str
    _speed_str: str
    _total_bytes_str: str
    _default_template: str


current_bar: Optional[ProgressBar] = None


def dl_hook(dl_step: DownloadStep):
    global current_bar

    if dl_step["status"] == "finished":
        print("Done downloading, now converting ...")
        if current_bar is not None:
            current_bar = None
    elif dl_step["status"] == "downloading":
        current_bar = current_bar or ProgressBar(max_value=dl_step["total_bytes"])
        current_bar.update(dl_step["downloaded_bytes"])


def pp_hook(d):
    if d["status"] == "finished":
        print("Done processing ...")


COMMON_ALBUM_PATTERNS = [
    re.compile(r"(?P<release_date>[0-9]{8}|NA) - (?P<album_artist>.*) - (?P<album>.*)"),
    re.compile(r"(?P<release_date>[0-9]{8}|NA) - (?P<album>.*)"),
]
COMMON_TRACK_PATTERNS = [
    re.compile(r"(?P<track_number>/d+) - (?P<artist>.*) - (?P<title>.*)"),
    re.compile(r"(?P<track_number>/d+) - (?P<title>.*)"),
    re.compile(r"(?P<track_number>Full) - (?P<artist>.*) - (?P<title>.*)"),
    re.compile(r"(?P<track_number>Full) - (?P<title>.*)"),
]

CURRENT_PUBLISHER_ALBUM_PATTERNS: list[Pattern] = []
CURRENT_PUBLISHER_TRACK_PATTERNS: list[Pattern] = []


class FileCleanerPostProcessor(PostProcessor):
    def run(self, information: Mapping) -> tuple[list, Mapping]:
        filepath = (
            Path(information["filepath"]) if information.get("filepath") else None
        )
        if not filepath:
            return [], information

        parent_folder = filepath.parent
        publisher, album_pathname = parent_folder.parts[-2:]

        if thumbnail := next(parent_folder.glob("*.jpg"), None):
            crop_edges(thumbnail, overwrite=True)

        tag_folder(
            parent_folder,
            CURRENT_PUBLISHER_ALBUM_PATTERNS + COMMON_ALBUM_PATTERNS,
            CURRENT_PUBLISHER_TRACK_PATTERNS + COMMON_TRACK_PATTERNS,
            thumbnail,
        )

        return [], information


def download_music(
    name: str,
    url: str,
    only_music: bool = True,
    last_date: Optional[str] = None,
    album_regexes: Optional[list[str]] = None,
    track_regexes: Optional[list[str]] = None,
):
    print("Download: " + name)

    _, _, _, ydl_opts = parse_options()

    ydl_opts.update(
        {
            "match_filter": match_filter_func("!is_live"),  # --match-filter !is_live
            "ignoreerrors": True,  # -i
            "writeinfojson": True,  # --write-info-json
            "overwrites": False,  # -w
            "continue_dl": False,  # --no-continue
            "updatetime": False,  # --no-mtime
            "outtmpl": {
                "default": r"%(channel)s/%(upload_date)s - %(title)s/Full - %(title)s.%(ext)s",
                "chapter": r"%(channel)s/%(upload_date)s - %(title)s/%(section_number)d - %(section_title)s.%(ext)s",
                "thumbnail": r"%(channel)s/%(upload_date)s - %(title)s/_ - thumbnail.%(ext)s",
            },
            "writethumbnail": True,
            "postprocessors": [
                {
                    "key": "FFmpegSplitChapters",
                    "force_keyframes": False,
                },
                {
                    "key": "FFmpegThumbnailsConvertor",
                    "format": "jpg",
                    "when": "before_dl",
                },
            ],
            "logger": MyLogger(),
            "progress_hooks": [dl_hook],
            "postprocessor_hooks": [pp_hook],
            "paths": {"home": str(MUSIC_PATH)},
            "break_on_reject": True,
        }
    )

    if only_music:
        print("Only as music")
        ydl_opts.update(
            {
                "format": "bestaudio/best",
            }
        )
        ydl_opts["postprocessors"].insert(
            0,
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "mp3",
                "preferredquality": "192",
            },
        )

    if last_date:
        dateafter = datetime.fromisoformat(last_date).strftime("%Y%m%d")
        print("Only videos more recent than " + dateafter)
        daterange = DateRange(dateafter, None)
        ydl_opts.update(daterange=daterange)

    global CURRENT_PUBLISHER_ALBUM_PATTERNS
    CURRENT_PUBLISHER_ALBUM_PATTERNS = []
    for regex in album_regexes or []:
        CURRENT_PUBLISHER_ALBUM_PATTERNS.append(re.compile(regex))

    global CURRENT_PUBLISHER_TRACK_PATTERNS
    CURRENT_PUBLISHER_TRACK_PATTERNS = []
    for regex in track_regexes or []:
        CURRENT_PUBLISHER_TRACK_PATTERNS.append(re.compile(regex))

    with YoutubeDL(ydl_opts) as ydl:
        ydl.add_post_processor(FileCleanerPostProcessor())
        try:
            ydl.download([url])
        except RejectedVideoReached as e:
            print("Boundary date reached. Passing")


class Channel(TypedDict):
    name: str
    url: str
    only_music: bool
    last_date: str
    album_regexes: list[str]
    track_regexes: list[str]


def main():
    CONFIG_PATH.mkdir(exist_ok=True)
    LAST_DLED_CHANNELS.touch(exist_ok=True)

    try:
        last_dled_channels = cast(list[Channel], json.load(LAST_DLED_CHANNELS.open()))
    except JSONDecodeError as e:
        print("Error while loading last_dled_channels: " + str(e))
        last_dled_channels = []

    for channel in last_dled_channels:
        download_music(
            channel["name"],
            channel["url"],
            channel.get("only_music", True),
            channel.get("last_date"),
            channel.get("album_regexes", []),
            channel.get("track_regexes", []),
        )
        channel["last_date"] = datetime.now().isoformat()

        json.dump(last_dled_channels, LAST_DLED_CHANNELS.open("w"), indent=4)


if __name__ == "__main__":
    main()
