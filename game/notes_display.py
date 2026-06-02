from utils import *
from .notes import TapNote, HoldNote, Coin, NoteData
from .surfer import Surfer
from kivy.utils import get_color_from_hex
from config import Sizes, Judge, Colors

def pos_to_x(pos):
    return (pos - 0.5) * Sizes.FIELD_WIDTH


class NoteDisplay(InstructionGroup):
    """Base class for scrolling note visuals. Subclasses set self.trans in __init__."""

    def __init__(self, game):
        super().__init__()
        self.game = game
        self.hit: float = None
        """when this note was hit"""
        self.hit_judge: Judge = None
        self.color = Color()
        """reference color for note hits"""

        with StackFrame(self):
            self.trans = Translate()
            self.add(self.trans)

            self._draw()

    def _draw(self):
        """override to draw the visual"""
        raise NotImplementedError

    def _refresh(self):
        """override to update the visual"""
        raise NotImplementedError

    def press(self, t, judge):
        self.hit = t
        self.hit_judge = judge
        self.color.rgb = Colors.JUDGES[judge].rgb

    def _scroll(self, t, beat):
        self.trans.y = -(t - float(beat)) * self.game.rate

    def _refresh_hit(self, t):
        """Call from subclass refresh when hit. Fades out; returns True when done."""
        self.color.a = slide(t - self.hit, 0, 0.5)(1, 0)
        self._refresh(t)
        return t - self.hit > 0.5

    def refresh(self, t):
        if self.hit is not None:
            return self._refresh_hit(t)
        self._scroll(t, self.beat)
        return self._refresh(t)


class TapDisplay(NoteDisplay):
    def __init__(self, game, note):
        self.note = note
        self.beat = self.note.beat
        super().__init__(game)

    def _draw(self):
        x1 = pos_to_x(self.note.left_end)
        x2 = pos_to_x(self.note.right_end)

        T = Sizes.TAP_THICK

        self.shadow_color = Color(0.7, 0.7, 0.7)
        self.add(self.shadow_color)
        self.add(BoxShadow(pos=(x1, -T/2), size=(x2-x1, T), border_radius=[T/2]*4))

        if self.note.hold:
            self.color.rgb = 0.5, 0.8, 1
        self.add(self.color)
        self.add(Rectangle(pos=(x1+T/2, -T/2), size=(x2-x1-T, T)))

        self.circle_color = Color(0.6, 0.7, 0.6)
        self.add(self.circle_color)
        self.add(Ellipse(pos=(x1, -T/2), size=(T, T)))
        self.add(Ellipse(pos=(x2-T, -T/2), size=(T, T)))

    def _refresh(self, t):
        r, g, b, a = self.color.rgba
        self.shadow_color.rgba = vmul(self.color.rgba, (.2, .1, .4, 1) if self.note.hold else (.7, .7, .7, 1))
        self.circle_color.rgba = vmul(self.color.rgba, (.6, .7, .9, 1) if self.note.hold else (.6, .7, .6, 1))

        return (t - float(self.note.beat)) > 2


TICK_RATE = 32


class HoldDisplay(NoteDisplay):
    def __init__(self, game, note):
        self.note = note
        self.beat = self.note.start_beat
        super().__init__(game)

    def _draw(self):
        x1 = pos_to_x(self.note.left_at(self.note.start_beat))
        x2 = pos_to_x(self.note.right_at(self.note.start_beat))

        T = Sizes.TAP_THICK

        # render slider body
        self.body_color = Color(0.5, 0.8, 1, 0.5)
        self.add(self.body_color)
        self.mesh = self.calculate_mesh()
        self.mesh.mode = "triangle_strip"
        self.add(self.mesh)

    def calculate_mesh(self):
        vertices = []
        num_ticks = int((self.note.end_beat - self.note.start_beat) * TICK_RATE)
        for i in range(0, num_ticks + 1):
            t = i / TICK_RATE
            y = t * self.game.rate
            x1 = pos_to_x(self.note.left_at(t + self.note.start_beat))
            x2 = pos_to_x(self.note.right_at(t + self.note.start_beat))
            vertices.append((x1, y))
            vertices.append((x2, y))
        return mesher(vertices)

    def recalculate(self):
        mesh = self.calculate_mesh()
        self.mesh.vertices = mesh.vertices

    def activate(self):
        self.body_color.a = 0.75

    def release(self):
        self.body_color.a = 0.25

    def _refresh(self, t):
        return t - float(self.note.end_beat) > 2


class CoinDisplay(NoteDisplay):
    def __init__(self, game, note):
        self.note = note
        self.beat = self.note.beat
        super().__init__(game)

    def _draw(self):
        r = Sizes.COIN_SIZE / 2

        self.add(Color(0.1, 0.1, 0.1, 0.3))
        self.add(Ellipse(pos=(pos_to_x(self.note.position)-r,-r), size=(r*2,r*2)))

    def collect(self, t):
        self.press(t, Judge.PERFECT)

    def _refresh(self, t):
        return (t - float(self.note.beat)) > 2


class CoinDisplay2(NoteDisplay):
    def __init__(self, game, note):
        self.note = note
        self.beat = self.note.beat
        super().__init__(game)

    def _draw(self):
        self.remove(self.trans)

        r = Sizes.COIN_SIZE / 2

        self.add(Translate(Sizes.OBSERVER[0], Sizes.OBSERVER[1]))
        self.scale = Scale()
        self.add(self.scale)
        self.add(Translate(0, -Sizes.OBSERVER[1]))

        self.add(Translate(pos_to_x(self.note.position), Sizes.COIN_SIZE))

        self.outer_color = Color()
        self.add(self.outer_color)
        self.add(BoxShadow(pos=(-r,-r), size=(r*2,r*2), border_radius=(r,)*4))

        self.inner_color = Color()
        self.add(self.inner_color)
        self.add(Line(circle = (0,0,2/3*r),width = r/3))

    def collect(self, t):
        self.press(t, Judge.PERFECT)

    def _refresh(self, t):
        self.scale.xyz = (Sizes.OBSERVER[2] / (self.trans.y + self.game.now_depth + Sizes.OBSERVER[2]),)*3
        fade = clamp(0, 1, 2 * (1 - (self.trans.y + self.game.now_depth) / Sizes.FIELD_DEPTH))
        self.inner_color.rgba = vmul(self.color.rgba, (1, 0.55, 0.1, 1))
        self.outer_color.rgba = vmul(self.color.rgba, (1, 0.4, 0.1, 0.5))
        self.inner_color.a *= fade
        self.outer_color.a *= fade
        return (t - float(self.note.beat)) > 2


class NotesDisplay(InstructionGroup):
    def __init__(self, game, note_data):
        super().__init__()
        self.game = game

        self._taps = sorted(note_data.tap_notes, key=lambda n: n.beat)
        self._holds = sorted(note_data.hold_notes, key=lambda n: n.start_beat)
        self._coins = sorted(note_data.coins, key=lambda c: c.beat)

        self._next_tap = 0
        self._next_hold = 0
        self._next_coin = 0

        self._hold_group = InstructionGroup()
        self._tap_group = InstructionGroup()
        self._coin_group = InstructionGroup()
        self.add(self._hold_group)
        self.add(self._tap_group)
        self.add(self._coin_group)

        self.coin_group2 = InstructionGroup()

        self._tap_displays = {}  # TapNote  -> TapDisplay
        self._hold_displays = {}  # HoldNote -> HoldDisplay
        self._coin_displays = {}  # Coin     -> CoinDisplay
        self._coin_displays2 = {} # Coin -> CoinDisplay2

    def reset(self):
        """Call when scrubbing backward so notes re-spawn correctly."""
        self._next_tap = 0
        self._next_hold = 0
        self._next_coin = 0
        self._hold_group.clear()
        self._tap_group.clear()
        self._coin_group.clear()
        self.coin_group2.clear()
        self._tap_displays.clear()
        self._hold_displays.clear()
        self._coin_displays.clear()
        self._coin_displays2.clear()

    def _spawn(self, t):
        lk = Sizes.FIELD_DEPTH / self.game.rate
        while (
            self._next_tap < len(self._taps)
            and float(self._taps[self._next_tap].beat) <= t + lk
        ):
            note = self._taps[self._next_tap]
            d = TapDisplay(self.game, note)
            self._tap_displays[id(note)] = d
            self._tap_group.add(d)
            self._next_tap += 1

        while (
            self._next_hold < len(self._holds)
            and float(self._holds[self._next_hold].start_beat) <= t + lk
        ):
            note = self._holds[self._next_hold]
            d = HoldDisplay(self.game, note)
            self._hold_displays[id(note)] = d
            self._hold_group.add(d)
            self._next_hold += 1

        while (
            self._next_coin < len(self._coins)
            and float(self._coins[self._next_coin].beat) <= t + lk
        ):
            note = self._coins[self._next_coin]
            d = CoinDisplay(self.game, note)
            self._coin_displays[id(note)] = d
            self._coin_group.add(d)
            d2 = CoinDisplay2(self.game, note)
            self._coin_displays2[id(note)] = d2
            self.coin_group2.insert(0, d2)
            self._next_coin += 1

    def on_tap_hit(self, note, t, judge):
        if id(note) in self._tap_displays:
            display = self._tap_displays[id(note)]
            display.press(t, judge)
            if display.note.hold:
                self._hold_displays[id(display.note.hold)].activate()

    def on_tick_hit(self, note, t, beat):
        if id(note) in self._hold_displays:
            self._hold_displays[id(note)].activate()

    def on_tick_miss(self, note, t, beat):
        if id(note) in self._hold_displays:
            self._hold_displays[id(note)].release()

    def on_coin_collect(self, note, t):
        if id(note) in self._coin_displays:
            self._coin_displays[id(note)].collect(t)
            self._coin_displays2[id(note)].collect(t)

    def recalculate(self):
        for hold in self._hold_group.children:
            hold.recalculate()

    def refresh(self, t):
        self._spawn(t)
        for group, lookup in (
            (self._tap_group, self._tap_displays),
            (self._hold_group, self._hold_displays),
            (self._coin_group, self._coin_displays),
            (self.coin_group2, self._coin_displays2),
        ):
            for item in group.children.copy():
                if item.refresh(t):
                    group.remove(item)
                    lookup.pop(id(item.note), None)
