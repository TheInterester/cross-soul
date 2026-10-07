from utils import *
import config as cfg
from config import Texts, Colors
from widgets.song_related import Difficulty

Builder.load_string("""
#: import C config.Colors
#: import utils utils
#: import Color kivy.graphics.Color

<Setting>:
    size_hint: None, None
    DrawLabel:
        pos: 0, 0
        text: self.parent.label
        variant: "Bold"
        font_size: self.parent.font_size
        color: C.LAVENDER.rgba
        kwargs: { "outline_width": self.parent.font_size * 1.5, "outline_color": utils.darken(C.LAVENDER).rgba }
    DrawLabel:
        pos: self.parent.drop
        text: self.parent.info
        variant: "Bold"
        font_size: self.parent.font_size * .75
        color: self.parent.color
        kwargs: { "outline_width": self.parent.font_size * .75 * 1.5, "outline_color": utils.darken(Color(rgba=self.parent.color)).rgba }


<Loop2>:
    size_hint: None, None
    canvas:
        Color:
            rgba: C.VIOLET.rgba
        Line:
            rounded_rectangle: 0, 0, self.width, self.height, self.radius
            width: self.thickness / 2 * 3
        Color:
            rgba: C.BORDER.rgba
        Line:
            rounded_rectangle: 0, 0, self.width, self.height, self.radius
            width: self.thickness / 2


<SpeedButton>:
    size_hint: None, None
    size: 35, 25
    canvas:
        Color:
            rgba: C.PALEPURPLE.rgba
        RoundedRectangle:
            size: self.size
            radius: [(5, 5)]
    DrawLabel:
        pos: self.parent.width/2, self.parent.height/2
        text: self.parent.label
        variant: "Bold"
        font_size: 25
        color: C.PURPLE.rgba


<SpeedControl>:
    size_hint: None, None
    size: 250, 40
    center: 0, 0
    GlitchRect:
        glitch1: C.AZURE.rgba
        glitch2: C.VIOLET.rgba
        bg: C.PURPLE.rgba
    DrawLabel:
        pos: self.parent.width/2, self.parent.height/2
        text: self.parent.text
        variant: "Bold"
        font_size: 25
        color: C.BORDER.rgba
    SpeedButton:
        pos_hint: { "center": (.1, .5) }
        label: "−−"
    SpeedButton:
        pos_hint: { "center": (.275, .5) }
        label: "−"
    SpeedButton:
        pos_hint: { "center": (.725, .5) }
        label: "+"
    SpeedButton:
        pos_hint: { "center": (.9, .5) }
        label: "++"


<DifficultyControl>:
    size_hint: None, None
    size: 250, 30
    center: 0, 0
    GlitchRect:
        glitch1: C.VIOLET.rgba
        glitch2: C.VIOLET.rgba
        bg: C.INVIS.rgba
""")


class Setting(RelativeLayout):
    color = ColorProperty([1, 1, 1, 1])
    label = StringProperty("??")
    info = StringProperty("??")
    font_size = NumericProperty(0)
    drop = ListProperty([0, 0])


class Loop2(RelativeLayout):
    "Configuration list."
    def __init__(self):
        super().__init__()
        self.setts = []
        for i in range(4):
            # TODO create different class
            d = Setting()
            d.info = ""
            d.label = ["LEVEL", "SPEED", "VIEW", "PLAY!"][i] # VIEW does nothing, could replace
            d.color = Colors.WHITE.rgba
            self.setts.append(d)
            self.add_widget(d)
        self.refresh()

    def refresh(self):
        for i, d in enumerate(self.setts):
            d.pos = self.width/2 + (i - (4 - 1)/2) * self.width/4, 0
            d.font_size = 20
            d.drop = 0, 22

    thickness = NumericProperty(1.75)
    radius = NumericProperty(0)


class SpeedButton(RelativeLayout):
    label = StringProperty("?")


class SpeedControl(RelativeLayout):
    def __init__(self):
        super().__init__()

    text = StringProperty("?.??")


class DifficultyControl(RelativeLayout):
    def __init__(self, diffs):
        super().__init__()
        self.diffs = []
        for i, diff in enumerate(diffs):
            if i >= cfg.DIFFS:
                warn("Too many difficulties provided!")
                break
            if diff is None:
                self.diffs.append(None)
                continue
            d = Difficulty()
            d.name = Texts.DIFF_NAMES[i]
            d.level = f"{diff:02}"
            d.color = Colors.DIFFS[i].rgba
            d.pos = self.width/2 + (i - (cfg.DIFFS - 1)/2) * self.width/4, self.height
            d.font_size = 30
            d.drop = 0, -self.height
            self.diffs.append(d)
            self.add_widget(d)
