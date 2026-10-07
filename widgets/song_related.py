from utils import *
import config as cfg
from config import Texts, Colors

Builder.load_string("""
#: import C config.Colors
#: import utils utils
#: import Color kivy.graphics.Color

<Jacket>:
    canvas:
        Color
        Rectangle:
            source: self.source
            size: self.size
        Color:
            rgba: C.BORDER.rgba
        Line:
            rectangle: (-2, -2, self.size[0]+4, self.height+4)
            width: 1.5

<Card>:
    size_hint: None, None
    size: 100, 140
    center: 0, 0
    GlitchRect
    Jacket:
        source: self.parent.info.jacket
        size_hint: None, None
        size: self.parent.width * .75, self.parent.width * .75
        pos: (self.parent.width-self.width) / 2, self.parent.height - ((self.parent.width+self.width) / 2)
    DrawLabel:
        pos: self.parent.width / 2, 30
        text: self.parent.info.title.upper()
        variant: "Bold"
        font_size: 12
        color: C.BORDER.rgba
    DrawLabel:
        pos: self.parent.width / 2, 20
        text: self.parent.info.artist.upper()
        font_size: 10
        color: C.BORDER.rgba

<Board>:
    size_hint: None, None
    size: 150, 90
    center: 0, 0
    GlitchRect:
        glitch1: C.AZURE.rgba
        glitch2: C.VIOLET.rgba
        bg: C.LAVENDER.rgba
    DrawLabel:
        pos: 5, self.parent.height - 5
        anchor: 0, 1
        text: "" # TODO never idk
        font_size: 10
        color: C.BORDER.rgba

<Difficulty>:
    size_hint: None, None
    DrawLabel:
        pos: 0, 0
        text: self.parent.level
        variant: "Bold"
        font_size: self.parent.font_size
        color: self.parent.color
        kwargs: { "outline_width": self.parent.font_size * 1.5, "outline_color": utils.darken(Color(rgba=self.parent.color)).rgba }
    DrawLabel:
        pos: self.parent.drop
        text: self.parent.name
        variant: "Bold"
        font_size: self.parent.font_size * .75
        color: self.parent.color
        kwargs: { "outline_width": self.parent.font_size * .75 * 1.5, "outline_color": utils.darken(Color(rgba=self.parent.color)).rgba }

<Selector>:
    size_hint: None, None
    canvas:
        Color:
            rgba: [*self.color[0:3], self.color[3] * .25]
        RoundedRectangle:
            pos: -self.width/2, -self.height/2
            size: self.size
            radius: [(self.radius, self.radius)]
""")


class Jacket(RelativeLayout):
    "Framed image."
    source = StringProperty()


class Card(RelativeLayout):
    "Song selection entry."

    def __init__(self, info):
        self.info = info
        super().__init__()


class Board(RelativeLayout):
    "Leaderboard."
    pass

class Difficulty(RelativeLayout):
    "Difficulty text."
    color = ColorProperty([1, 1, 1, 1])
    level = StringProperty("??")
    name = StringProperty("??")
    font_size = NumericProperty(0)
    drop = ListProperty([0, 0])


class Selector(RelativeLayout):
    "Highlights selected thing."
    color = ColorProperty([1, 1, 1, 1])
    radius = NumericProperty(10)
