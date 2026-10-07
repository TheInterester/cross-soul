from kivy.core.window import Window
from kivy.graphics import Color, Line, Rectangle, Ellipse
from imslib.core import BaseWidget, run
from imslib.gfxutil import CEllipse
from imslib.mixer import Mixer
from imslib.wavesrc import WaveFile
from game.audio import *
from game.notes import TapNote, Coin, NoteData, HoldNote, ControlPoint
from fractions import Fraction
from utils import *
import sys
import os
import tkinter as tk
from tkinter import filedialog

sys.path.insert(0, os.path.abspath(".."))
from imslib.gfxutil import topleft_label, resize_topleft_label, CLabelRect
import math

RATE = 120  # pixels per beat
SNAP = Fraction(1, 4)  # grid resolution
NOTE_W = 1 / 14  # default tap width as fraction of window width
HANDLE_R = 10  # hit-test radius for drag handles (pixels)

NUM_LANES = 14


def y_at_beat(beat, scroll):
    return float(beat - scroll) * RATE


def beat_at_y(y, scroll):
    raw = Fraction(scroll) + Fraction(y) / Fraction(RATE)
    return raw.limit_denominator(64)


def time_to_snap(ac: AudioController):
    snap = snap_beat(ac.get_beat())
    return (snap, ac.get_beat() - snap)


def snap_beat(beat):
    return Fraction(round(float(beat) / float(SNAP))) * SNAP


def x_at_pos(pos):
    return pos * Window.width


def snap_pos(x):
    return round(x * (NUM_LANES)) / (NUM_LANES)


def pos_at_x(x):
    return max(0.0, min(1.0, x / Window.width))


def dist(x1, y1, x2, y2):
    return math.hypot(x1 - x2, y1 - y2)


class ControlPointDisplay(InstructionGroup):
    R = 8

    def __init__(
        self,
        point: ControlPoint,
        next: ControlPoint | None = None,
        linked_point: ControlPoint | None = None,
        link_mode="none",
        scroll=0,
    ):
        super().__init__()
        self.control_point = point
        self.next = next
        self.linked_point = linked_point
        self.link_mode = "none"

        self.selected = False
        self.color = Color(0.94, 0.9, 0.18, 0.8)
        self.change_type(point.curve)
        R = ControlPointDisplay.R
        y = y_at_beat(self.control_point.beat, scroll)
        x = x_at_pos(self.control_point.pos)
        self.circle = CEllipse(cpos=(x, y), size=(R * 2, R * 2))
        self.line = Line(points=(x, y, 0, 0), width=1)
        self.add(self.color)
        if not self.next is None:
            y2 = y_at_beat(self.next.beat, scroll)
            x2 = x_at_pos(self.next.pos)
            self.line.points = [x, y, x2, y2]
            self.add(self.line)
        self.add(self.circle)
        self.add(Color(0.94, 0.9, 0.18, 0.8))
        self.select_circle = CEllipse(cpos=(x, y), size=(R * 2 + 4, R * 2 + 4))

    def change_type(self, type):
        match type:
            case "linear":
                self.color.rgba = [0.8, 0.1, 0.2, 0.9]
                self.control_point.curve = "linear"
            case "bezier":
                self.color.rgba = [0.94, 0.9, 0.18, 0.8]
                self.control_point.curve = "bezier"

    def change_link_mode(self, mode):
        self.link_mode = mode

    def change_linked_point(self, linked_point):
        self.linked_point = linked_point

    def add_next(self, control_point: ControlPoint, scroll):
        self.next = control_point
        self.calculate_line(scroll)

    def remove_next(self, scroll):
        if not self.next is None:
            self.next = self.next.next
        self.calculate_line(scroll)

    def calculate_line(self, scroll):
        y = y_at_beat(self.control_point.beat, scroll)
        x = x_at_pos(self.control_point.pos)
        if not self.next is None:
            y2 = y_at_beat(self.next.beat, scroll)
            x2 = x_at_pos(self.next.pos)
            self.line.points = [x, y, x2, y2]
            if not self.line in self.children:
                self.add(self.line)
        elif self.line in self.children:
            self.remove(self.line)

    def set_select(self, select):
        self.selected = select
        if select and not self.select_circle in self.children:
            self.add(self.select_circle)
        elif not select and self.select_circle in self.children:
            self.remove(self.select_circle)

    def on_update(self, scroll):
        R = ControlPointDisplay.R
        self.calculate_line(scroll)
        y = y_at_beat(self.control_point.beat, scroll)
        x = x_at_pos(self.control_point.pos)
        self.circle.set_cpos((x, y))
        self.select_circle.set_cpos((x, y))
        if self.next is None:
            return -R <= y <= Window.height + R
        else:
            y2 = y_at_beat(self.next.beat, scroll)
            return 0 <= y2 <= Window.height or -R <= y <= Window.height + R


class ControlPointsDisplay(InstructionGroup):
    def __init__(self, points: list[ControlPoint], scroll=0):
        super().__init__()
        self.points = points
        self.point_displays = []  # type: list[ControlPointDisplay]
        for i in range(len(self.points)):
            next = self.points[i + 1] if i + 1 < len(self.points) else None
            new_point = ControlPointDisplay(self.points[i], next, scroll)
            self.point_displays.append(new_point)
            self.add(new_point)

        self.selected = None

    # add control point after idx
    def add_control_point(self, control_point, idx: int, scroll):
        next_point = self.points[idx + 1]
        prev_display = self.point_displays[idx]
        new_display = ControlPointDisplay(control_point, next_point, scroll)
        prev_display.add_next(control_point, scroll)
        self.points.insert(idx + 1, control_point)
        self.point_displays.insert(idx + 1, new_display)
        self.add(new_display)
        beats = [point.beat for point in self.points]
        print(beats)

    def set_select(self, select):
        if self.selected is not None:
            self.selected.set_select(False)
        self.selected = select
        if select is not None:
            select.set_select(True)

    def on_update(self, scroll):
        return render_children(self, self.point_displays, scroll)


class HoldDisplayEditor(InstructionGroup):
    def __init__(self, hold_note: HoldNote, scroll=0):
        super().__init__()
        self.selected = False
        self.hold_note = hold_note

        self.left_cpd = ControlPointsDisplay(self.hold_note.left_pts, scroll)
        self.right_cpd = ControlPointsDisplay(self.hold_note.right_pts, scroll)

        self.render_instructions = []
        self.calculate_instructions()
        self.ct = 0

        self.color = Color(0.4, 1, 0.2, 0.8)
        self.add(self.color)
        self.add(PushMatrix())
        self.trans = Translate(0, 0)
        self.add(self.trans)
        for instr in self.render_instructions:
            self.add(instr)
        self.add(PopMatrix())

        if self.selected:
            self.add(self.left_cpd)
            self.add(self.right_cpd)

        # TODO: Fix hold note bezier rendering

    def calculate_instructions(self):
        get_xy = lambda point: [x_at_pos(point.pos), y_at_beat(point.beat, 0)]

        def calculate_side(cpd: ControlPointsDisplay):
            points = cpd.points
            bezier_save = []
            linear_save = []
            for point in points:
                if point.curve == "linear":
                    linear_save.extend(get_xy(point))
                    if len(bezier_save) != 0:
                        self.render_instructions.append(
                            Line(bezier=bezier_save, cap="none")
                        )
                        bezier_save.clear()
                elif point.curve == "bezier":
                    bezier_save.extend(get_xy(point))
                    if len(linear_save) != 0:
                        self.render_instructions.append(
                            Line(points=linear_save, cap="none")
                        )
                        linear_save.clear()
            if len(bezier_save) != 0:
                self.render_instructions.append(Line(bezier=bezier_save, cap="none"))
            if len(linear_save) != 0:
                self.render_instructions.append(Line(points=linear_save, cap="none"))

        self.render_instructions.append(
            Line(
                points=[
                    *get_xy(self.left_cpd.points[0]),
                    *get_xy(self.right_cpd.points[0]),
                ],
                cap="none",
            )
        )
        self.render_instructions.append(
            Line(
                points=[
                    *get_xy(self.left_cpd.points[-1]),
                    *get_xy(self.right_cpd.points[-1]),
                ],
                cap="none",
            )
        )
        calculate_side(self.left_cpd)
        calculate_side(self.right_cpd)

    def recalculate_ends(self, point: ControlPoint):
        first_left = self.hold_note.left_pts[0]
        first_right = self.hold_note.right_pts[0]
        last_left = self.hold_note.left_pts[-1]
        last_right = self.hold_note.right_pts[-1]
        if point is first_left:
            first_right.beat = point.beat
            self.hold_note.start_beat = point.beat
        elif point is first_right:
            first_left.beat = point.beat
            self.hold_note.start_beat = point.beat
        elif point is last_left:
            last_right.beat = point.beat
            self.hold_note.end_beat = point.beat
        elif point is last_right:
            last_left.beat = point.beat
            self.hold_note.end_beat = point.beat

    def rerender(self):

        self.render_instructions.clear()
        self.calculate_instructions()

        self.clear()
        self.add(self.color)
        with StackFrame(self):
            self.add(self.trans)
            for instr in self.render_instructions:
                self.add(instr)
        if self.selected:
            self.add(self.left_cpd)
            self.add(self.right_cpd)

    def set_select(self, select):
        self.selected = select
        if select:
            if self.left_cpd not in self.children:
                self.add(self.left_cpd)
            if self.right_cpd not in self.children:
                self.add(self.right_cpd)
        else:
            if self.left_cpd.selected is not None:
                self.left_cpd.set_select(None)
            elif self.right_cpd.selected is not None:
                self.right_cpd.set_select(None)
            if self.left_cpd in self.children:
                self.remove(self.left_cpd)
            if self.right_cpd in self.children:
                self.remove(self.right_cpd)

    def on_update(self, scroll):
        left = self.left_cpd.on_update(scroll)
        right = self.right_cpd.on_update(scroll)
        self.trans.y = y_at_beat(0, scroll)
        self.rerender()
        return left | right


class TapDisplayEditor(InstructionGroup):
    def __init__(self, tap_note: TapNote, scroll=0):
        super().__init__()
        self.selected = False
        self.drag = "none"
        self.tap_note = tap_note

        y = y_at_beat(self.tap_note.beat, scroll)
        xl = x_at_pos(self.tap_note.left_end)
        xr = x_at_pos(self.tap_note.right_end)

        self.bar_color = Color(1, 1, 1, 1)
        self.bar = Line(points=[xl, y, xr, y], width=2)
        self.left_color = Color(0.2, 0.8, 1, 0.9)
        self.left_circle = CEllipse(pos=(xl, y), size=(HANDLE_R * 2, HANDLE_R * 2))
        self.right_color = Color(0.2, 0.8, 1, 0.9)
        self.right_circle = CEllipse(pos=(xr, y), size=(HANDLE_R * 2, HANDLE_R * 2))

        self.add(self.bar_color)
        self.add(self.bar)
        self.add(self.left_color)
        self.add(self.left_circle)
        self.add(self.right_color)
        self.add(self.right_circle)

    def set_select(self, select):
        self.selected = select
        if select:
            self.bar_color.rgba = [1, 1, 1, 1]
        else:
            self.bar_color.rgba = [0.7, 0.7, 0.7, 0.9]

    def set_drag(self, drag_string):
        self.drag = drag_string
        match drag_string:
            case "none":
                self.left_color.rgba = [0.2, 0.8, 1, 0.9]
                self.right_color.rgba = [0.2, 0.8, 1, 0.9]
            case "left":
                self.left_color.rgba = [0.8, 0.1, 0.2, 0.9]
                self.right_color.rgba = [0.2, 0.8, 1, 0.9]
                self.set_select(True)
            case "right":
                self.left_color.rgba = [0.2, 0.8, 1, 0.9]
                self.right_color.rgba = [0.8, 0.1, 0.2, 0.9]
                self.set_select(True)

    def on_update(self, scroll):
        y = y_at_beat(self.tap_note.beat, scroll)
        xl = x_at_pos(self.tap_note.left_end)
        xr = x_at_pos(self.tap_note.right_end)
        self.bar.points = [xl, y, xr, y]
        self.left_circle.set_cpos((xl, y))
        self.right_circle.set_cpos((xr, y))
        return -HANDLE_R - 2 <= y <= Window.height + HANDLE_R + 2


class CoinDisplayEditor(InstructionGroup):
    def __init__(self, coin: Coin, scroll=0):
        super().__init__()
        self.coin = coin
        self.selected = False
        R = 12

        xp = x_at_pos(self.coin.position)
        y = y_at_beat(self.coin.beat, scroll)

        # coin circle
        self.main_color = Color(1, 0.55, 0.1, 0.9)
        self.add(self.main_color)
        self.coin_circle = CEllipse(pos=(xp, y), size=(R * 2, R * 2))
        self.add(self.coin_circle)
        # drag handle (same position, drawn on top)
        self.drag_color = Color(0.2, 0.8, 1, 0.9)
        self.add(self.drag_color)
        self.drag_circle = CEllipse(pos=(xp, y), size=(HANDLE_R * 2, HANDLE_R * 2))
        self.add(self.drag_circle)

    def set_select(self, select):
        self.selected = select
        self.drag_color.r = 1 if self.selected else 0.2

    def on_update(self, scroll):
        R = 12
        xp = x_at_pos(self.coin.position)
        y = y_at_beat(self.coin.beat, scroll)
        self.coin_circle.set_cpos((xp, y))
        self.drag_circle.set_cpos((xp, y))

        return -R - HANDLE_R <= y <= Window.height + R + HANDLE_R


class ChartEditor(BaseWidget):
    def __init__(self):
        super().__init__()
        self.scroll = Fraction(0)
        self.v_off = 0

        self.mixer = Mixer()
        w_shiawase = WaveFile("./assets/shiawase.wav")
        self.ac = AudioController(self.mixer, w_shiawase, 150, -0.06)
        AUDIO.set_generator(self.mixer)
        self.ac.pause()
        self.filename = ""
        self.changed = False

        self.mode = "TAP"  # 'TAP' | 'COIN' | 'HOLD'
        self.taps = []  # type: list[TapNote]
        self.tap_displays = []  # type: list[TapDisplayEditor]
        self.coins = []  # type: list[Coin]
        self.coin_displays = []  # type: list[CoinDisplayEditor]
        self.holds = []  # type: list[HoldNote]
        self.hold_displays = []  # type: list[HoldDisplayEditor]
        self._drag = None  # (obj, field) where field is left, right or pos for the coin
        self._selected = None
        self._selected_control_point = None
        self.metadata = {}  # type: dict[str, str]
        self.info = topleft_label()
        self.add_widget(self.info)

        self._update_info_text()
        self._hold_start = None
        # nd = NoteData.from_file('./assets/shiawase.txt')

    def on_key_down(self, keycode, modifiers):
        global SNAP, RATE
        k = keycode[1]
        step = Fraction(4) if "shift" in modifiers else Fraction(1)
        if k == "up":
            self.scroll = max(Fraction(0), self.scroll - step)
            self.ac.scrub(-step)
        elif k == "down":
            self.scroll += step
            self.ac.scrub(step)
        elif k == "right":
            SNAP = Fraction(1, SNAP.denominator * 2)
        elif k == "left":
            SNAP = Fraction(1, max(1, int(SNAP.denominator / 2)))
        elif k == "=":  # mental models as +
            RATE = RATE + 15
        elif k == "-":
            RATE = max(RATE - 15, 90)
        elif k == "t":
            self.mode = "TAP"
        elif k == "c":
            self.mode = "COIN"
        elif k == "h":
            self.mode = "HOLD"
        elif k == "delete" or k == "backspace":
            if self._selected is not None:
                if self._selected in self.tap_displays:
                    self.tap_displays.remove(self._selected)
                    self.taps.remove(self._selected.tap_note)
                    self.changed = True
                    self.deselect()
                elif self._selected in self.hold_displays:
                    self.hold_displays.remove(self._selected)
                    self.holds.remove(self._selected.hold_note)
                    self.changed = True
                    self.deselect()
                elif self._selected in self.coin_displays:
                    self.coin_displays.remove(self._selected)
                    self.coins.remove(self._selected.coin)
                    self.changed = True
                    self.deselect()
                self._selected = None
        elif k == "s" and "ctrl" in modifiers:
            if self.filename == "":
                base = "./assets/shiawase_new"
                suffix = ".txt"
                ct = 0
                while os.path.exists(base + suffix):
                    ct += 1
                    suffix = f"_{ct}.txt"
                self._save(base + suffix)
            else:
                self._save(self.filename)
        elif k == "o" and "ctrl" in modifiers:
            filename = filedialog.askopenfilename(initialdir=os.path.dirname(__file__))
            if not filename == "":
                if self.filename == "":
                    base = "./assets/shiawase_new"
                    suffix = ".txt"
                    ct = 0
                    while os.path.exists(base + suffix):
                        ct += 1
                        suffix = f"_{ct}.txt"
                    if self.changed:
                        self._save(base + suffix)
                else:
                    if self.changed:
                        self._save(self.filename)
                print("attempting read...")
                self.read_from_file(filename)
        elif k == "spacebar":
            self.ac.toggle()
        elif k == "1":
            if self._selected_control_point is not None:
                self._selected_control_point.change_type("linear")
        elif k == "2":
            if self._selected_control_point is not None:
                self._selected_control_point.change_type("bezier")

    def read_from_file(self, filename):
        note_data = NoteData.from_file(filename)
        self.deselect()
        self.scroll = 0
        self.v_off = 0
        self.ac.pause()
        self.ac.reset()
        self.taps = note_data.tap_notes
        self.metadata = note_data.metadata
        bpm = note_data.bpm
        offset = note_data.offset
        url = self.metadata["url"]
        self.ac = AudioController(self.mixer, WaveFile(url), bpm, offset)
        self.tap_displays = [
            TapDisplayEditor(tap_note, self.scroll) for tap_note in self.taps
        ]
        self.coins = note_data.coins
        self.coin_displays = [
            CoinDisplayEditor(coin, self.scroll) for coin in self.coins
        ]
        self.holds = note_data.hold_notes
        self.hold_displays = [
            HoldDisplayEditor(hold_note, self.scroll) for hold_note in self.holds
        ]
        self.filename = filename
        self.changed = False

    def _save(self, path):
        # merge and sort all notes by beat
        rows = (
            [("TAP", n.beat, n) for n in self.taps]
            + [("COIN", c.beat, c) for c in self.coins]
            + [("HOLD", h.start_beat, h) for h in self.holds]
        )
        rows.sort(key=lambda r: r[1])
        lines = []
        for kind, beat, obj in rows:
            if kind == "TAP":
                lines.append(f"TAP  {beat}  {obj.left_end:.4f}  {obj.right_end:.4f}")
            elif kind == "COIN":
                lines.append(f"COIN {beat}  {obj.position:.4f}")
            elif kind == "HOLD":
                lines.append(f"HOLD {beat} {obj.end_beat}")
                for pt in obj.left_pts:
                    lines.append(f"\tL {pt.beat} {pt.pos} {pt.curve}")
                for pt in obj.right_pts:
                    lines.append(f"\tR {pt.beat} {pt.pos} {pt.curve}")
        with open(path, "w") as f:
            f.write(f"BPM {self.ac.bps * 60}\n")
            f.write(f"OFFSET {self.ac.off}\n")
            for key, value in self.metadata.items():
                f.write(f"{key.upper()} {value}\n")
            f.write("\n".join(lines) + "\n")
        print(f"Saved {len(self.taps)} taps + {len(self.coins)} coins to {path}")

    def on_touch_down(self, touch):
        # scrolling the chart
        if touch.is_mouse_scrolling:
            delta = Fraction(1, 4)
            if touch.button == "scrolldown":
                self.scroll += delta
                self.ac.scrub(delta)
            elif touch.button == "scrollup":
                self.scroll = max(Fraction(0), self.scroll - delta)
                self.ac.scrub(-delta)
            return True

        # check for nearby notes
        true_scroll = self.scroll + self.v_off
        for tap_display in self.tap_displays:
            tap_note = tap_display.tap_note
            y = y_at_beat(tap_note.beat, true_scroll)
            xl = x_at_pos(tap_note.left_end)
            xr = x_at_pos(tap_note.right_end)
            if dist(touch.x, touch.y, xl, y) < HANDLE_R:
                self.deselect()
                self._drag = (tap_note, "left")
                tap_display.set_drag("left")
                self._selected = tap_display
                return True
            if dist(touch.x, touch.y, xr, y) < HANDLE_R:
                self.deselect()
                self._drag = (tap_note, "right")
                tap_display.set_drag("right")
                self._selected = tap_display
                return True
            if dist(touch.x, touch.y, touch.x, y) < HANDLE_R and xl <= touch.x < xr:
                self.deselect()
                self._drag = (tap_note, "pos")
                tap_display.set_drag("none")
                tap_display.set_select(True)
                self._selected = tap_display
                return True

        for coin_display in self.coin_displays:
            coin = coin_display.coin
            y = y_at_beat(coin.beat, true_scroll)
            xp = x_at_pos(coin.position)
            if dist(touch.x, touch.y, xp, y) < HANDLE_R:
                self.deselect()
                self._drag = (coin, "position")
                self._selected = coin_display
                coin_display.set_select(True)
                return True

        for hold in self.hold_displays:
            if hold in self.canvas.children:
                for control_point in hold.left_cpd.point_displays:
                    point = control_point.control_point
                    y = y_at_beat(point.beat, true_scroll)
                    x = x_at_pos(point.pos)
                    if dist(x, y, touch.x, touch.y) < HANDLE_R:
                        self.deselect()
                        self._drag = (point, "pos")
                        self._selected = hold
                        self._selected_control_point = control_point
                        control_point.set_select(True)
                        hold.set_select(True)
                        hold.left_cpd.set_select(control_point)
                        return True

                for control_point in hold.right_cpd.point_displays:
                    point = control_point.control_point
                    y = y_at_beat(point.beat, true_scroll)
                    x = x_at_pos(point.pos)
                    if dist(x, y, touch.x, touch.y) < HANDLE_R:
                        self.deselect()
                        self._drag = (point, "pos")
                        self._selected = hold
                        self._selected_control_point = control_point
                        control_point.set_select(True)
                        hold.set_select(True)
                        hold.right_cpd.set_select(control_point)
                        return True

        # otherwise we place new note based on note type
        beat = snap_beat(beat_at_y(touch.y, true_scroll))
        pos = pos_at_x(touch.x)

        # if hold selected, check ctrl-click for new control point creation
        if isinstance(self._selected, HoldDisplayEditor):
            if "ctrl" in Window.modifiers:
                new_ctrl = ControlPoint(beat, pos)
                # assume linked mode for now
                # controlpoints need to be in sequential order in all cases
                left = self._selected.left_cpd
                right = self._selected.right_cpd
                l_idx = 0
                while l_idx < len(left.points) and left.points[l_idx].beat < beat:
                    l_idx += 1
                r_idx = 0
                while r_idx < len(right.points) and right.points[r_idx].beat < beat:
                    r_idx += 1
                print(l_idx)
                if l_idx == len(left.points):
                    l_dist = float("inf")
                else:
                    prev_x, prev_y = x_at_pos(left.points[l_idx - 1].pos), y_at_beat(
                        left.points[l_idx - 1].beat, true_scroll
                    )
                    next_x, next_y = x_at_pos(left.points[l_idx].pos), y_at_beat(
                        left.points[l_idx].beat, true_scroll
                    )
                    line_x = (touch.y - prev_y) / (next_y - prev_y) * (
                        next_x - prev_x
                    ) + prev_x
                    l_dist = abs(line_x - touch.x)
                if r_idx == len(right.points):
                    r_dist = float("inf")
                else:
                    prev_x, prev_y = x_at_pos(right.points[r_idx - 1].pos), y_at_beat(
                        right.points[r_idx - 1].beat, true_scroll
                    )
                    next_x, next_y = x_at_pos(right.points[r_idx].pos), y_at_beat(
                        right.points[r_idx].beat, true_scroll
                    )

                    line_x = (touch.y - prev_y) / (next_y - prev_y) * (
                        next_x - prev_x
                    ) + prev_x
                    r_dist = abs(line_x - touch.x)

                if l_dist < r_dist:
                    print("left closer")
                    print(l_dist, r_dist)
                    left.add_control_point(new_ctrl, l_idx - 1, true_scroll)
                    self.changed = True
                    return True
                else:
                    print("right closer")
                    print(l_dist, r_dist)
                    right.add_control_point(new_ctrl, r_idx - 1, true_scroll)
                    self.changed = True
                    return True

        if self.mode == "TAP":
            half = NOTE_W / 2
            new_tap = TapNote(
                beat=beat,
                left_end=snap_pos(max(0.0, pos - half)),
                right_end=snap_pos(min(1.0, pos + half)),
            )
            self.taps.append(new_tap)
            self.tap_displays.append(TapDisplayEditor(new_tap, true_scroll))
            self.changed = True
        elif self.mode == "COIN":
            new_coin = Coin(beat=beat, position=pos)
            self.coins.append(new_coin)
            self.coin_displays.append(CoinDisplayEditor(new_coin, true_scroll))
            self.changed = True
        elif self.mode == "HOLD":
            self._hold_start = (beat, pos)
            left_pos = snap_pos(pos - NOTE_W / 2)
            right_pos = snap_pos(pos + NOTE_W / 2)
            left_points = [
                ControlPoint(beat, left_pos),
                ControlPoint(beat + 2, left_pos),
            ]
            right_points = [
                ControlPoint(beat, right_pos),
                ControlPoint(beat + 2, right_pos),
            ]
            new_hold = HoldNote(beat, beat + 2, left_points, right_points)
            self.holds.append(new_hold)
            self.hold_displays.append(HoldDisplayEditor(new_hold, true_scroll))
            self.changed = True

        return True

    def on_touch_move(self, touch):
        """dragging things if we have selected."""
        true_scroll = self.scroll + self.v_off
        if self._drag is None:
            return

        obj, field = self._drag
        pos = pos_at_x(touch.x)
        old_beat = obj.beat
        beat = snap_beat(beat_at_y(touch.y, true_scroll))
        obj.beat = beat
        if old_beat != beat and isinstance(obj, ControlPoint):
            self._selected.recalculate_ends(obj)
        if field == "left":
            obj.left_end = snap_pos(min(pos, obj.right_end - 0.01))
            self.changed = True
        elif field == "right":
            obj.right_end = snap_pos(max(pos, obj.left_end + 0.01))
            self.changed = True
        elif field == "pos":
            obj.pos = snap_pos(pos)
            self.changed = True
        elif field == "position":
            obj.position = pos
            self.changed = True
        # if isinstance(obj, ControlPoint) and isinstance(self._selected, HoldDisplayEditor):
        #     hold = self._selected.hold_note
        #     is_on_left = obj in hold.left_pts
        #     hold.start_beat = min(hold.start_beat, obj.beat)

    def on_touch_up(self, touch):
        self._drag = None

    def _update_info_text(self):
        beat_str = (
            str(self.scroll) if self.scroll.denominator != 1 else str(int(self.scroll))
        )
        self.info.text = (
            f"mode: {self.mode}  |  beat: {beat_str}\n"
            f"\n"
            f"[t] tap  [c] coin [h] hold (not finished implementation)\n"
            f"[up/down] scroll 1 beat  [shift+up/down] scroll 4 beats\n"
            f"scroll wheel: 1/4 beat\n"
            f"click: place note  drag handles: adjust\n"
            f"[s] save"
        )

    def on_update(self):
        self.canvas.clear()
        with self.canvas:
            self._draw_grid()
            self._draw_mode_indicator()
            self._update_info_text()
        AUDIO.on_update()
        self.scroll, self.v_off = time_to_snap(self.ac)
        self.update_coins()
        self.update_taps()
        self.update_holds()

    def _draw_grid(self):
        true_scroll = self.scroll + self.v_off
        lo = int(float(self.scroll))
        hi = lo + int(Window.height / RATE) + 2
        for i in range(lo, hi + 1):
            for sub in range(16):
                b = Fraction(i) + Fraction(sub, 16)
                y = y_at_beat(b, true_scroll)
                if not (-2 <= y <= Window.height + 2):
                    continue
                if sub == 0:  # measure downbeat (whole beat multiple of 4)
                    a, w = (0.6, 1.5) if i % 4 == 0 else (0.3, 1.0)
                elif sub % 4 == 0:  # quarter beat
                    a, w = 0.15, 0.8
                else:  # 16th
                    a, w = 0.05, 0.5
                Color(1, 1, 1, a)
                Line(points=[0, y, Window.width, y], width=w)
        for i in range(1, NUM_LANES):
            Color(1, 1, 1, 0.7)
            x = x_at_pos(i / NUM_LANES)
            Line(points=[x, 0, x, Window.height])

    def _draw_mode_indicator(self):
        # small coloured square in top-left corner showing current mode
        if self.mode == "TAP":
            Color(1, 1, 1)
        elif self.mode == "COIN":
            Color(1, 0.55, 0.1)
        elif self.mode == "HOLD":
            Color(0.7, 1, 0.1)
        Rectangle(pos=(10, Window.height - 30), size=(20, 20))

    def deselect(self):
        if self._selected in self.coin_displays:
            self._selected.set_select(False)
        if self._selected in self.tap_displays:
            self._selected.set_select(False)
            self._selected.set_drag("none")
        if self._selected in self.hold_displays:
            self._selected.set_select(False)
        self._selected = None
        self._selected_control_point = None

    def update_taps(self):
        true_scroll = self.scroll + self.v_off
        for td in self.tap_displays:
            vis = td.on_update(true_scroll)
            render = td in self.children
            if vis and not render:
                self.canvas.add(td)
            if not vis and render:
                self.canvas.remove(td)

    def update_coins(self):
        true_scroll = self.scroll + self.v_off
        for cd in self.coin_displays:
            vis = cd.on_update(true_scroll)
            render = cd in self.children
            if vis and not render:
                self.canvas.add(cd)
            if not vis and render:
                self.canvas.remove(cd)

    def update_holds(self):
        true_scroll = self.scroll + self.v_off
        for hd in self.hold_displays:
            vis = hd.on_update(true_scroll)
            render = hd in self.canvas.children
            if vis and not render:
                self.canvas.add(hd)
            if not vis and render:
                self.canvas.remove(hd)


if __name__ == "__main__":
    run(ChartEditor())
