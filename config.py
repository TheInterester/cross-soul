from kivy.utils import get_color_from_hex

from utils import *

def chex(hash):
    return Color(*get_color_from_hex(hash))

LANES = 14
LANER_KEYS = ["tab"] + [*"qwertyuiop[]\\"]
assert LANES == len(LANER_KEYS)
DIFFS = 4

class Judge(Enum):
    """Timing judgments."""
    PERFECT = 0.015
    FANTASTIC = 0.023
    GREAT = 0.045
    OKAY = 0.075
    BAD = 0.120
    MISS = None

class Weights:
    """For scoring."""
    JUDGE = {
        Judge.PERFECT: 5,
        Judge.FANTASTIC: 4,
        Judge.GREAT: 3,
        Judge.OKAY: 2,
        Judge.BAD: 1,
        Judge.MISS: 0,
    }
    COIN = 1
    TICK = 1

MAX_SCORE = 1_250_000
THRESHOLDS = [
    (1_200_000, "SSS", Judge.PERFECT),
    (1_100_000, "SS+", Judge.PERFECT),
    (1_000_000, "SS", Judge.PERFECT),
    (900_000, "S+", Judge.FANTASTIC),
    (800_000, "S", Judge.FANTASTIC),
    (700_000, "A+", Judge.GREAT),
    (600_000, "A", Judge.GREAT),
    (500_000, "B+", Judge.OKAY),
    (400_000, "B", Judge.OKAY),
    (300_000, "C+", Judge.BAD),
    (200_000, "C", Judge.BAD),
    (100_000, "D+", Judge.MISS),
    (0, "D", Judge.MISS),
]

TICK_TIME = Judge.BAD.value
"""seconds between each tick"""
HITSTUN = 0.5
"""hitstun time in seconds"""

class Colors:
    BORDER = Color(hsv=(286/360, 1, .34))
    """a softer black"""

    PALE = Color(hsv=(0, 0, .9))
    """a softer white"""
    LAVENDER = chex("#f3c7ff")
    """an off-white"""
    PURPLE = chex("#ceb6ff")
    """another off-white"""
    PALEPURPLE = chex("#eaddfe")
    """an inner off-white"""
    INVIS = Color(a=0)
    """transparent"""

    CYAN = Color(hsv=(180/360, 1, 1))
    """glitch effect color 1"""
    MAGENTA = Color(hsv=(300/360, 1, 1))
    """glitch effect color 2"""
    AZURE = chex("#38b6ff")
    """glitch dark 1"""
    VIOLET = chex("#8c52ff")
    """glitch dark 2"""

    PINK = chex("#f79bff")
    """ranger unselected"""
    HOTPINK = chex("#f156ff")
    """ranger selected"""
    GRAY = chex("#acacac")
    """ranger disabled"""
    WHITE = Color(hsv=(0, 0, 1))

    DIFFS = [
        chex("#00d8ff"),
        chex("#00ff57"),
        chex("#ffca4c"),
        chex("#ff5757"),
    ]

    JUDGES = {
        Judge.PERFECT: Color(hsv=(3 / 6, 0, 1)),  # white
        Judge.FANTASTIC: Color(hsv=(3 / 6, 1, 1)),  # cyan
        Judge.GREAT: Color(hsv=(1 / 3, 1, 1)),  # green
        Judge.OKAY: Color(hsv=(1 / 6, 1, 1)),  # yellow
        Judge.BAD: Color(hsv=(1 / 12, 1, 1)),  # orange
        Judge.MISS: Color(hsv=(0, 1, 1)),  # red
    }

    TICK_HIT = Color(hsv=(3 / 6, 0, 1))
    TICK_MISS = Color(hsv=(3 / 6, 0, .5))

    COIN_COLLECT = Color(hsv=(3 / 6, 0, 1))
    COIN_MISS = Color(hsv=(0, 1, 1))

class Texts:
    DIFF_NAMES = ["EZ", "NM", "HD", "XT"]

    JUDGES = {
        Judge.PERFECT: "PERFECT!!",
        Judge.FANTASTIC: "FANTASTIC!",
        Judge.GREAT: "GREAT",
        Judge.OKAY: "OKAY..",
        Judge.BAD: "BAD...",
        Judge.MISS: "MISS",
    }

    TICK_HIT = "COOL"
    TICK_MISS = "DROP"

    COIN_COLLECT = "GOT!"
    COIN_MISS = "LOST"

class Sizes:
    FIELD_WIDTH = 400
    """width of the note field"""
    FIELD_DEPTH = 4000
    """Depth of the note field to draw."""
    BARLINE_THICK = 4
    """thickness of barlines"""
    LANEDIV_THICK = 1
    """thickness of lane dividers"""
    TAP_THICK = 10
    """thickness of tap notes"""
    COIN_SIZE = 25
    """diameter of coins"""
    OBSERVER = (200, 300, 400)
    """X, Y: Screen offset of the viewer/vanishing point.
    Z: Distance the viewer is from the screen, for perspective calculation."""
