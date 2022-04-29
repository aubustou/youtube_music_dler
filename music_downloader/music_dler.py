import json
import re
import subprocess
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from typing import Mapping, Optional, TypedDict, cast

from mutagen.easyid3 import EasyID3
from mutagen.mp3 import MP3
from yt_dlp import parse_options
from yt_dlp.postprocessor.common import PostProcessor
from yt_dlp.utils import DateRange, RejectedVideoReached, match_filter_func
from yt_dlp.YoutubeDL import YoutubeDL

from .crop_covers import crop_edges

MUSIC_PATH = Path().home() / "Musique"
MUSIC_LIST = MUSIC_PATH / "musique.lst"
CONFIG_PATH = Path.home() / ".yt-downloader"
LAST_DLED_CHANNELS = CONFIG_PATH / "last_dled_channels.json"


class MyLogger:
    def debug(self, msg):
        print(msg)

    def warning(self, msg):
        print(msg)

    def error(self, msg):
        print(msg)


def dl_hook(d):
    if d["status"] == "finished":
        print("Done downloading, now converting ...")


def pp_hook(d):
    if d["status"] == "finished":
        print("Done processing ...")


def to_tags(file_: Path) -> None:
    comment, album_pathname, _ = file_.parts[-3:]
    try:
        date, albumartist, album = (x.strip() for x in album_pathname.split("-", 3))
    except (TypeError, ValueError):
        date, album = (x.strip() for x in album_pathname.split("-", 2))
        albumartist = comment

    filename = file_.stem
    for hyphen in ["–"]:
        filename = filename.replace(hyphen, "-")

    try:
        tracknumber, artist, title = (x.strip() for x in filename.split("-", 3))
    except (TypeError, ValueError):
        tracknumber, title = (x.strip() for x in filename.split("-", 2))
        artist = albumartist

    date = f"{date[:4]}-{date[4:6]}-{date[6:]}"

    print("Save tags on ", str(file_))

    mp3file = MP3(file_, ID3=EasyID3)
    mp3file["album"] = album
    mp3file["albumartist"] = albumartist
    mp3file["artist"] = artist
    mp3file["date"] = date
    mp3file["title"] = title
    mp3file["tracknumber"] = "1" if tracknumber == "Full" else tracknumber

    mp3file.save()


class FileCleanerPostProcessor(PostProcessor):
    def run(self, information: Mapping) -> tuple[list, Mapping]:
        filepath = (
            Path(information["filepath"]) if information.get("filepath") else None
        )
        if not filepath:
            return [], information

        files = list(filepath.parent.glob("*.mp3"))
        if len(files) == 1:
            to_tags(files[0])
        else:
            for file_ in files:
                if file_.name.startswith("Full"):
                    print("Remove full file " + str(file_))
                    file_.unlink()
                    continue

                to_tags(file_)

        if thumbnail := next(filepath.parent.glob("*.jpg"), None):
            crop_edges(thumbnail, overwrite=True)

        return [], information


def download_music_internal(
    name: str, url: str, only_music: bool = True, last_date: Optional[str] = None
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

    with YoutubeDL(ydl_opts) as ydl:
        ydl.add_post_processor(FileCleanerPostProcessor())
        try:
            ydl.download([url])
        except RejectedVideoReached as e:
            print("Boundary date reached. Passing")


def download_music_external(
    name: str, url: str, only_music: bool = True, last_date: Optional[str] = None
):
    print("Download: " + name)
    cmd = [
        "yt-dlp",
        # "--netrc",
        "--match-filter",
        "!is_live",
        "--match-filter",
        "!was_live",
        "-i",
        "--write-info-json",
        "-w",
        "--no-continue",
        "--no-mtime",
        "--split-chapters",
    ]

    if only_music:
        cmd += [
            "-x",
            "--audio-format",
            "mp3",
        ]
    if last_date:
        cmd += ["--dateafter", datetime.fromisoformat(last_date).strftime("%Y%m%d")]

    cmd += [
        "-o",
        "%(channel)s\%(upload_date)s - %(title)s\Full - %(title)s.%(ext)s",
        "-o",
        "chapter:%(channel)s\%(upload_date)s - %(title)s\%(section_number)d - %(section_title)s.%(ext)s",
        "--write-thumbnail",
        "-o",
        "thumbnail:%(channel)s\%(upload_date)s - %(title)s\_ - thumbnail.%(ext)s",
        "--convert-thumbnails",
        "jpg",
        url,
    ]
    process = subprocess.run(cmd, cwd=MUSIC_PATH, shell=True, capture_output=True)

    ignore_errors = False

    if process.returncode:
        stderr = process.stderr.decode()
        print(stderr)
        if (
            "ERROR: This live stream recording is not available" in stderr
            or "ERROR: Sign in to confirm your age" in stderr
        ):
            ignore_errors = True

    if only_music and (process.returncode == 0 or ignore_errors):
        output = process.stdout.decode(errors="ignore")
        full_files = re.findall(r"\[download\] Destination:\s(.*)", output)

        if not full_files:
            return

        artist_folder_path = MUSIC_PATH / Path(full_files[0]).parents[1]
        for music_folder in artist_folder_path.iterdir():
            if not music_folder.is_dir():
                continue
            if list(music_folder.glob("1 - *.mp3")):
                full_file_path = next((music_folder.glob("Full - *.mp3")), None)
                if full_file_path:
                    print("Remove full fill as chapters exist: ", str(full_file_path))
                    full_file_path.unlink()

            for file_ in music_folder.glob("*.mp3"):
                infos = {}

                match = re.match(
                    r"(?P<album_artist>.*)\\(?P<year>[0-9]{8}) - (?P<album>.*)\\(?P<track>[0-9]+) - (?P<artist>.*) (?:-|–) (?P<title>.*).mp3",
                    str(file_),
                )

                if match:
                    infos = match.groupdict()

                else:
                    match = re.match(
                        r".*\\(?P<year>[0-9]{8}) - (?P<album_artist>.*) - (?P<album>.*)\\Full - (?P<artist>.*) (?:-|–) (?P<title>.*).mp3",
                        str(file_),
                    )
                    if match:
                        infos = match.groupdict()
                        infos["track"] = 1

                if not infos:
                    continue

                path = MUSIC_PATH / Path(file_)
                if not path.exists():
                    # Problème d'encodage certainement
                    continue

                print("Save tags on ", str(path))


def download_music(
    name: str, url: str, only_music: bool = True, last_date: Optional[str] = None
):
    download_music_internal(name, url, only_music, last_date)


class Channel(TypedDict):
    name: str
    url: str
    only_music: bool
    last_date: str


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
        )
        channel["last_date"] = datetime.now().isoformat()

        json.dump(last_dled_channels, LAST_DLED_CHANNELS.open("w"), indent=4)


if __name__ == "__main__":
    main()
