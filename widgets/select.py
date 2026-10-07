from utils import *
import config as cfg
from config import Texts, Colors
from data import get_card_info
from widgets.common import Placer
from widgets.song_related import Difficulty, Card

Builder.load_string("""
#: import C config.Colors
#: import utils utils
#: import Color kivy.graphics.Color

<Loop>:
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
""")


class Loop(RelativeLayout):
    "Difficulty list."
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
            self.diffs.append(d)
            self.add_widget(d)
        self.refresh()

    def refresh(self):
        for i, d in enumerate(self.diffs):
            if d is None:
                continue
            d.pos = self.width/2 + (i - (cfg.DIFFS - 1)/2) * self.width/4, self.height
            d.font_size = self.width/8 + 4
            d.drop = 0, -self.height

    thickness = NumericProperty(1.75)
    radius = NumericProperty(0)


class Cards(RelativeLayout):
    """Song select."""

    def _pos_from_offset(self, i):
        """given relative index, returns card pos, scale and line pos, size, radius, rot"""
        x = 200 + i * 87
        x -= lerp(0, 20 + 300 * self.split, clamp(0, 1, -i))
        x += lerp(0, 20 + 300 * self.split, clamp(0, 1, i))
        selected = max(0, 1 - abs(i))
        y = 100 + lerp(0, 5, selected)
        scale = lerp(.75, 1, selected)
        x2 = x - lerp(0, 80, selected)
        y2 = y + lerp(55, 120 + 400 * self.split, selected)
        w = lerp(65, 200, selected)
        h = lerp(20, 30, selected)
        r = lerp(0, 8, selected)
        ra = lerp(8, 15, selected)
        return (x, y), scale, (x2 - w/2, y2 - h/2), (w, h), ra, r

    def __init__(self, i, songs_list, card):
        super().__init__()

        self.vi = i
        """visual position, lags behind actual selection"""
        self.split = 0
        """for transition in/out"""

        self.songs_list = songs_list

        self.cards: dict[int, tuple[Placer, Placer]] = {}
        if card is not None:
            loop = Placer(Loop(self.info(i).levels))  # TODO data
            self.add_widget(loop)
            self.add_widget(card)
            self.cards[i] = card, loop

        self._refresh()

    def info(self, i):
        return get_card_info(self.songs_list[i % len(self.songs_list)])

    def _refresh(self):
        vi = round(self.vi)
        for i in list(self.cards):
            if abs(i - vi) > 3:
                card, loop = self.cards[i]
                self.remove_widget(card)
                self.remove_widget(loop)
                del self.cards[i]
        for i in range(vi - 3, vi + 4):
            if i not in self.cards:
                info = self.info(i)
                loop = Placer(Loop(info.levels))
                self.add_widget(loop)
                card = Placer(Card(info))
                self.add_widget(card)
                self.cards[i] = card, loop
            pos, scale, pos2, size, radius, rot = self._pos_from_offset(i - self.vi)
            card, loop = self.cards[i]
            card.set_pos(pos)
            card.set_scale(scale)
            card.opacity = slide(abs(i - self.vi), 3, 3.5)(1, 0)
            loop.set_pos(pos2)
            loop.set_angle(rot)
            loop.widget.size = size
            loop.widget.radius = radius
            loop.widget.refresh()

    def update(self, dt, i):
        self.vi = approach(self.vi, i, dt * 5)
        self.opacity = slide(self.split, .5, 1)(1, 0)
        self._refresh()
