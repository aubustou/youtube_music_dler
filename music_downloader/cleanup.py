from pathlib import Path

for folder in Path("K:\Mp3\Boxon").iterdir():

    if not folder.is_dir():
        continue
    for music_folder in folder.iterdir():
        files = list(music_folder.glob("*"))
        if (
            len(files) == 2
            and (music_folder / "_ - thumbnail.jpg").exists()
            and list(music_folder.glob("*.json"))
        ):
            print(f"{str(music_folder)} - {len(files)}")
            try:
                for file_ in music_folder.iterdir():
                    file_.unlink()
                music_folder.rmdir()
            except FileNotFoundError:
                print("error")
