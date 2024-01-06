import re
from pathlib import Path
from typing import Optional, Pattern

from mutagen.easyid3 import EasyID3
from mutagen.id3 import APIC, ID3, TALB, TIT2, TPE1, TPE2, TPUB, TRCK, TSO2, TYER
from mutagen.mp3 import MP3

USE_EASYID3 = False
USE_REGEXES = False

HYPHENS = {"–", "—", "–"}
TO_CLEAN = {"\u200e", "\u2060"}
PREFIXES = [
    "the ",
    "le ",
    "la ",
    "les ",
    "l'",
    "die ",
    "der ",
    "das ",
    "de ",
    "el ",
    "los ",
    "las ",
]


def tag_folder(
    folder: Path,
    channel_album_regexes: list[Pattern],
    channel_track_regexes: list[Pattern],
    cover_path: Optional[Path] = None,
):
    files = list(folder.glob("*.mp3"))

    publisher, album_pathname = folder.parts[-2:]

    for hyphen in HYPHENS:
        album_pathname = album_pathname.replace(hyphen, "-")

    for to_clean in TO_CLEAN:
        album_pathname = album_pathname.replace(to_clean, "")

    album = ""
    release_date = ""
    album_artist = ""

    for regex in channel_album_regexes:
        match = regex.match(album_pathname)
        if match:
            album = match.groupdict().get("album", "").rstrip()
            album_artist = match.groupdict().get("album_artist", "").rstrip()
            release_date = match.groupdict().get("release_date", "").rstrip()
            break

    if not (album and release_date):
        print(f"Problem with album and release date on {album_pathname}")

    if len(release_date) == 8:
        release_date = f"{release_date[:4]}-{release_date[4:6]}-{release_date[6:]}"

    if not album_artist:
        album_artist = publisher

    album_artist_sort = None
    for prefix in PREFIXES:
        if album_artist.lower().startswith(prefix):
            album_artist_sort = (
                f"{album_artist[len(prefix):]}, {album_artist[:len(prefix)].rstrip()}"
            )
            break
    else:
        album_artist_sort = album_artist

    if len(files) == 1:
        to_tags(
            files[0],
            album=album,
            album_artist=album_artist,
            album_artist_sort=album_artist_sort,
            release_date=release_date,
            cover_path=cover_path,
            publisher=publisher,
            channel_track_regexes=channel_track_regexes,
        )
    else:
        for file_ in files:
            if file_.name.startswith("Full"):
                print("Remove full file " + str(file_))
                file_.unlink()
                continue

            to_tags(
                file_,
                album=album,
                album_artist=album_artist,
                album_artist_sort=album_artist_sort,
                release_date=release_date,
                cover_path=cover_path,
                publisher=publisher,
                channel_track_regexes=channel_track_regexes,
            )


def to_tags(
    file_: Path,
    album: str,
    album_artist: Optional[str],
    album_artist_sort: Optional[str],
    release_date: str,
    cover_path: Optional[Path],
    publisher: str,
    channel_track_regexes: list[Pattern],
) -> Optional[int]:
    filename = file_.stem

    for hyphen in HYPHENS:
        filename = filename.replace(hyphen, "-")
    for to_clean in TO_CLEAN:
        filename = filename.replace(to_clean, "")

    track_number = ""
    artist = ""
    title = ""

    regex_index = None

    for regex_index, regex in enumerate(channel_track_regexes):
        match = regex.match(filename)
        if match:
            track_number = match.groupdict().get("track_number", "").rstrip()
            artist = match.groupdict().get("artist", "").rstrip()
            title = match.groupdict().get("title", "").rstrip()
            break

    if not (track_number and title):
        print(f"Problem with title and track number on {filename}")

    if not artist:
        artist = album_artist

    print("Save tags on ", str(file_))

    track_number = "1" if track_number == "Full" else track_number

    if USE_EASYID3:
        mp3file = MP3(file_, ID3=EasyID3)
        mp3file["album"] = album
        mp3file["albumartist"] = album_artist
        mp3file["artist"] = artist
        mp3file["date"] = release_date
        mp3file["title"] = title
        mp3file["tracknumber"] = track_number
    else:
        mp3file = MP3(file_)
        try:
            mp3file.delete()
        except Exception:
            pass
        mp3file["TALB"] = TALB(encoding=3, text=album)
        mp3file["TIT2"] = TIT2(encoding=3, text=title)
        mp3file["TPE1"] = TPE1(encoding=3, text=artist)
        mp3file["TPE2"] = TPE2(encoding=3, text=album_artist)
        mp3file["TPUB"] = TPUB(encoding=3, text=publisher)
        mp3file["TRCK"] = TRCK(encoding=3, text=track_number)
        mp3file["TYER"] = TYER(encoding=3, text=release_date)
        mp3file["TSO2"] = TSO2(encoding=3, text=album_artist_sort)

        if cover_path:
            mp3file["APIC"] = APIC(
                encoding=3,
                mime="image/jpeg",
                type=3,
                desc="Cover",
                data=cover_path.read_bytes(),
            )

    mp3file.save()

    return regex_index


def main():
    CURRENT_ALBUM_PATTERNS = [
        # re.compile(
        #     r"(?:[0-9]{8}|NA) - (?P<album_artist>.*)(?:\s)*- (?P<album>.*) \(Full (?:Album|EP) (?P<release_date>\d+)\)"
        # ),
        # re.compile(
        #     r"(?:[0-9]{8}|NA) - (?P<album_artist>.*) - (?P<album>.*) (?P<release_date>\d+)"
        # ),
        re.compile(
            r"(?:[0-9]{8}|NA) - (?P<album_artist>.*) - (?P<album>.*) \((?P<release_date>\d+)\)"
        ),
        re.compile(
            r"(?:[0-9]{8}|NA) - (?P<album_artist>.*) ' (?P<album>.*) -(?:\s*)\((?P<release_date>\d+)\)"
        ),
    ]
    CURRENT_TRACK_PATTERNS = [
        re.compile(r"(?P<track_number>\d+) - (?:\d+\w*)(?:\s)*\.(?:\s)*(?P<title>.*)"),
        # re.compile(r"(?P<track_number>\d+) - (?:\d+)(?:\s)*-(?:\s)*(?P<title>.*)"),
        # re.compile(r"(?P<track_number>\d+) - (?:\d+) (?P<title>.*)"),
    ]

    from music_downloader.music_dler import COMMON_ALBUM_PATTERNS, COMMON_TRACK_PATTERNS

    for folder in Path("/home/aubustou/Musique/chansons françaises").iterdir():
        thumbnail = next(folder.glob("*.jpg"), None)
        tag_folder(
            folder,
            CURRENT_ALBUM_PATTERNS + COMMON_ALBUM_PATTERNS,
            CURRENT_TRACK_PATTERNS + COMMON_TRACK_PATTERNS,
            thumbnail,
        )


if __name__ == "__main__":
    main()
