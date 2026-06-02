# notes.py — pure data, no Kivy
# All positions are 0.0–1.0 fractions across the slider width.
# All times are in BEATS (use AudioController.get_beat()).

from __future__ import annotations

from fractions import Fraction
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class TapNote:
    beat: Fraction  # when the note should be hit
    left_end: float  # 0.0–1.0
    right_end: float  # 0.0–1.0
    hold: HoldNote | None = None


@dataclass
class SlideNote:
    beat: Fraction
    direction: Literal["U", "D", "L", "R"]
    left_end: float
    right_end: float


@dataclass
class ControlPoint:
    """One knot on a hold-note boundary curve."""

    beat: Fraction
    pos: float  # 0.0–1.0 x position at this beat
    curve: Literal["linear", "bezier"] = "linear"  # interpolation *from* this knot


@dataclass
class HoldNote:
    """
    Hold note whose left/right edges follow arbitrary piecewise curves.

    Each boundary is a list of ControlPoints sorted by beat.
    'linear' : straight line between knots
    'bezier' : smooth-step ease between knots (S-curve)
    """

    start_beat: Fraction
    end_beat: Fraction
    left_pts: list[ControlPoint] = field(default_factory=list)
    right_pts: list[ControlPoint] = field(default_factory=list)

    def left_at(self, beat: Fraction) -> float:
        """Evaluate left boundary position at a given beat."""
        return _eval_boundary(self.left_pts, beat)

    def right_at(self, beat: Fraction) -> float:
        """Evaluate right boundary position at a given beat."""
        return _eval_boundary(self.right_pts, beat)

    def head(self) -> TapNote:
        return TapNote(
            beat=self.start_beat,
            left_end=self.left_at(self.start_beat),
            right_end=self.right_at(self.start_beat),
            hold=self, # TODO this is a really bad hack, but IDK how else to do simply
        )


def _eval_boundary(pts: list[ControlPoint], beat: Fraction) -> float:
    """Interpolate a boundary curve at the given beat. Extrapolates flat."""
    if not pts:
        return 0.0
    if beat <= pts[0].beat:
        return pts[0].pos
    if beat >= pts[-1].beat:
        return pts[-1].pos
    for a, b in zip(pts, pts[1:]):
        if a.beat <= beat <= b.beat:
            t = float((beat - a.beat) / (b.beat - a.beat))
            if a.curve == "bezier":
                t = t * t * (3.0 - 2.0 * t)  # smooth-step
            return a.pos + t * (b.pos - a.pos)
    return pts[-1].pos

def _eval_bezier(pts: list[ControlPoint], beat: Fraction, pt: ControlPoint) -> float:
    points_to_use = []
    i = pts.index(pt)
    while pts[i].curve == "bezier":
        points_to_use.append(pts[i])
        i += 1
    raise NotImplementedError


@dataclass
class Coin:
    beat: Fraction
    position: float  # 0.0–1.0 x fraction


class NoteData:
    """
    Holds all notes for a chart.

    Load from a .txt chart file with NoteData.from_file(path),
    or build manually for testing.
    """

    def __init__(self):
        self.bpm: float = 0
        self.offset: float = 0
        self.tap_notes: list[TapNote] = []
        self.slide_notes: list[SlideNote] = []
        self.hold_notes: list[HoldNote] = []
        self.coins: list[Coin] = []
        self.metadata: dict[str, str] = {}

    def total_scoreable(self, tick_rate=32):
        taps  = len(self.tap_notes)
        ticks = sum(int((n.end_beat - n.start_beat) * tick_rate) for n in self.hold_notes)
        return taps + ticks / tick_rate

    @classmethod
    def from_file(cls, path: str) -> "NoteData":
        """
        Parse a .txt chart file.  Format summary:

            TAP   <beat>  <left>  <right>
            SLIDE <beat>  <dir>   <left>  <right>
            HOLD  <start> <end>
                L <beat>  <pos>   [linear|bezier]
                R <beat>  <pos>   [linear|bezier]
            COIN  <beat>  <pos>

        Beats can be integers or fractions (e.g. 5/2).
        Lines starting with # are comments; blank lines are ignored.
        """
        nd = cls()
        with open(path) as f:
            lines = f.readlines()

        i = 0
        while i < len(lines):
            line = lines[i].strip()
            i += 1

            if not line or line.startswith("#"):
                continue

            parts = line.split()
            cmd = parts[0].upper()

            match cmd:
                case "TAP":
                    nd.tap_notes.append(
                        TapNote(
                            beat=Fraction(parts[1]),
                            left_end=float(parts[2]),
                            right_end=float(parts[3]),
                        )
                    )

                case "SLIDE":
                    nd.slide_notes.append(
                        SlideNote(
                            beat=Fraction(parts[1]),
                            direction=parts[2].upper(),
                            left_end=float(parts[3]),
                            right_end=float(parts[4]),
                        )
                    )

                case "HOLD":
                    start_beat = Fraction(parts[1])
                    end_beat = Fraction(parts[2])
                    left_pts: list[ControlPoint] = []
                    right_pts: list[ControlPoint] = []

                    # consume indented L/R lines until a non-indented line
                    while i < len(lines):
                        raw = lines[i]
                        if raw.strip() == "" or raw.strip().startswith("#"):
                            i += 1
                            continue
                        if not raw[0].isspace():
                            break  # back to outer loop — don't consume
                        i += 1
                        sub = raw.split()
                        side = sub[0].upper()
                        beat = Fraction(sub[1])
                        pos = float(sub[2])
                        curve = sub[3] if len(sub) > 3 else "linear"
                        cp = ControlPoint(beat=beat, pos=pos, curve=curve)
                        if side == "L":
                            left_pts.append(cp)
                        else:
                            right_pts.append(cp)

                    note = HoldNote(
                        start_beat=start_beat,
                        end_beat=end_beat,
                        left_pts=left_pts,
                        right_pts=right_pts,
                    )
                    nd.hold_notes.append(note)
                    nd.tap_notes.append(note.head())

                case "COIN":
                    nd.coins.append(
                        Coin(
                            beat=Fraction(parts[1]),
                            position=float(parts[2]),
                        )
                    )
                case "BPM":
                    nd.bpm = float(parts[1])
                case "OFFSET":
                    nd.offset = float(parts[1])
                case "PREVIEW_START":
                    nd.preview_start = float(parts[1])
                case "PREVIEW_LEN":
                    nd.preview_len = float(parts[1])
                case "URL":
                    nd.metadata["url"] = " ".join(parts[1:])
                case "TITLE":
                    nd.metadata["title"] = " ".join(parts[1:])
                case "ARTIST":
                    nd.metadata["artist"] = " ".join(parts[1:])
                case "JACKET":
                    nd.metadata["jacket"] = " ".join(parts[1:])

        return nd

    @classmethod
    def example(cls) -> "NoteData":
        """Load the bundled example chart (assets/shiawase.txt)."""
        return cls.from_file("./assets/shiawase.txt")
