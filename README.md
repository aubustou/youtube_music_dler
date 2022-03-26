# music_dler

Download the most recent videos from your favorite channels.
Keep only the music if you want to.
Split by tracks when possible.


## Configuration

Create a JSON file in a `~/.yt-downloader` folder named `last_dled_channels.json`.
This JSON file contains a list of dictionaries e.g.:
```json
[
  {
    "name": "Toto à la plage",
    "url": "https://www.youbut.com/channel/toto_a_la_plage/videos",
    "only_music": true,
  }
]
```

with `name` as the channel name (indicative, only used as folder name), `url` as the URL to the channel videos or playlists or whatever lists of videos as supported by yt-dl and `only_music` if you want to only keep the music (default: `False`)

Every dictionaries will be filled with an additional `last_date` value for keeping track of the latest downloaded videos.


## Launch

Create venv with Python 3.9+ in your repo folder:
```bash
python3.9 -m venv venv
```
Then install it with pip:
```bash
venv/bin/python -m pip install .
```
Make sure the configuration file `last_dled_channels.json`has been created first then launch with:
```bash
venv/bin/music_dler
```
Enjoy.
