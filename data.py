import os
from dataclasses import dataclass, field

# Functions/Classes for song data loading
def get_sets() -> list[os.DirEntry]:
    sets = []
    for obj in os.scandir("./songs"):
        if obj.is_dir():
            sets.append(obj.path)
    return sorted(sets)

def get_card_info(path: os.DirEntry):
    files = os.scandir(path)
    for file in files:
        if file.name.endswith(".xsh"):
            return parse_header(path, file)
    raise NameError(f"No .xsh file found in directory {path.path}")

@dataclass
class SongInfo:
    title: str = "[TITLE]"
    artist: str = "[ARTIST]"
    jacket: str = "./assets/music.png"
    levels: list[int | None] = field(default_factory=lambda: [None] * 4)
    maps: list[str | None] = field(default_factory=list)
    audio: str = ""
    bpm: float = 60.
    offset: float = 0.
    preview_start: float = 0.
    preview_len: float = 16.
    start: float = 0.

def parse_header(folder: os.DirEntry, path: os.DirEntry) -> SongInfo:
    with open(path, "r") as f:
        lines = f.read().split("\n")
    info = SongInfo()
    for line in lines:
        line = line.strip()
        if line == "" or line.startswith("#"):
            continue
        cmd, rest = line.split(maxsplit=1)
        match cmd:
            case "TITLE":
                info.title = rest
            case "ARTIST":
                info.artist = rest
            case "JACKET":
                info.jacket = os.path.join(folder, rest)
            case "LEVEL":
                info.levels = [None if i == "-" else int(i) for i in rest.split()]
            case "MAP":
                info.maps.append(os.path.join(folder, rest) if rest != "-" else None)
            case "AUDIO":
                info.audio = os.path.join(folder, rest)
            case "BPM":
                info.bpm = float(rest)
            case "OFFSET":
                info.offset = float(rest)
            case "PREVIEW_START":
                info.preview_start = float(rest)
            case "PREVIEW_LEN":
                info.preview_len = float(rest)
            case "START":
                info.start = float(rest)
    return info
