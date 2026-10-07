from utils import *
from config import Colors
from widgets.common import Placer, DrawLabel

class ScoreLabel(RelativeLayout):
    def __init__(self, game, score):
        super().__init__()
        self.t = None
        self.game = game
        self.target_score = score
        self.old_score = self.target_score
        self.score = self.target_score
        self.placer = Placer(RelativeLayout())
        self.back_label = DrawLabel(
            text="0000000",
            anchor=(.5, 1),
            variant="Bold",
            font_size=15,
            color=(*darken(Colors.WHITE).rgb, .3),
            kwargs={ "outline_width": 15, "outline_color": darken(Colors.WHITE).rgba },
        )
        self.back_label._refresh()
        self.placer.widget.add_widget(self.back_label)
        self.label = DrawLabel(
            anchor=(.5, 1),
            variant="Bold",
            font_size=15,
            color=Colors.WHITE.rgba,
            kwargs={ "outline_width": 15, "outline_color": darken(Colors.WHITE).rgba },
        )
        self.label._refresh()
        self.placer.widget.add_widget(self.label)
        self.add_widget(self.placer)

    def set_score(self, t, score):
        if t is not None:
            t /= self.game.ac.bps
        self.t = t
        self.old_score = self.score
        self.target_score = score

    def refresh(self, t):
        t /= self.game.ac.bps
        if self.t is None:
            t = 1
        else:
            t -= self.t
        self.placer.set_scale(slide(t, .2, .3)(1.1, 1))
        self.score = int(slide(t, 0, .5)(self.old_score, self.target_score))
        self.label.text = f"{self.score}".rjust(7, " ")
