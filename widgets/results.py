from utils import *
from config import Colors, Judge, Weights
from widgets.common import Placer, DrawLabel

Builder.load_string("""
#: import C config.Colors
#: import utils utils
#: import Color kivy.graphics.Color

<ResultsBoard>:
    size_hint: None, None
    size: 230, 140
    center: 0, 0
    GlitchRect:
        glitch1: C.AZURE.rgba
        glitch2: C.VIOLET.rgba
        bg: C.LAVENDER.rgba
    DrawLabel:
        pos: self.parent.width - 10, self.parent.height - 5
        anchor: 1, 1
        text: "RESULTS"
        font_size: 15
        color: C.BORDER.rgba
""")

class ResultsBoard(RelativeLayout):
    pass

class CompletionLabel(RelativeLayout):
    def __init__(self, value, total, kind=False):
        super().__init__()

        stotal = f"{total}"
        svalue = f"{value}"

        label = DrawLabel(
            text = f"{' ' * len(stotal)} / {stotal}",
            variant="Bold",
            font_size=12,
            anchor=(0, .5),
            color=Colors.LAVENDER.rgba,
            kwargs={ "outline_width": 12, "outline_color": Colors.BORDER.rgba },
        )
        label._refresh()
        self.add_widget(label)

        label1 = DrawLabel(
            text = "0" * (len(stotal) - len(svalue)),
            variant="Bold",
            font_size=12,
            anchor=(0, .5),
            color=(*Colors.LAVENDER.rgb, .25),
            kwargs={ "outline_width": 12, "outline_color": Colors.BORDER.rgba },
        )
        label1._refresh()
        self.add_widget(label1)

        for judge in Judge:
            if Weights.JUDGE[judge] * total <= value * Weights.JUDGE[Judge.PERFECT]:
                break
        label2 = DrawLabel(
            text = svalue.rjust(len(stotal), " "),
            variant="Bold",
            font_size=12,
            anchor=(0, .5),
            color=Colors.LAVENDER.rgba if kind else lighten(Colors.JUDGES[judge]).rgba,
            kwargs={ "outline_width": 12, "outline_color": Colors.BORDER.rgba },
        )
        label2._refresh()
        self.add_widget(label2)
