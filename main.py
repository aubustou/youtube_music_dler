import json
import subprocess
from datetime import datetime
from json import JSONDecodeError
from pathlib import Path
from typing import cast, Optional, TypedDict
import re
import eyed3
from yt_dlp.YoutubeDL import YoutubeDL

MUSIC_PATH = Path("K:\Mp3\Boxon")
MUSIC_LIST = MUSIC_PATH / "musique.lst"
CONFIG_PATH = Path.home() / ".yt-downloader"
LAST_DLED_CHANNELS = CONFIG_PATH / "last_dled_channels.json"


def download_music_(
    name: str, url: str, only_music: bool = True, last_date: Optional[str] = None
):
    ydl_opts = {}
    with YoutubeDL(ydl_opts) as ydl:
        ydl.download([url])


def download_music(
    name: str, url: str, only_music: bool = True, last_date: Optional[str] = None
):
    print("Download: " + name)
    cmd = [
        MUSIC_PATH / "yt-dlp.exe",
        "--netrc",
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
        if "ERROR: This live stream recording is not available" in stderr or "ERROR: Sign in to confirm your age" in stderr:
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

                audiofile = eyed3.load(path)
                if not audiofile.tag.artist:
                    audiofile.tag.artist = infos["artist"]
                    audiofile.tag.album = infos["album"]
                    audiofile.tag.album_artist = infos["album_artist"]
                    audiofile.tag.title = infos["title"]
                    audiofile.tag.track_num = int(infos["track"])
                    audiofile.tag.release_date = infos["year"][:4]

                    audiofile.tag.save()


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
    except JSONDecodeError:
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
