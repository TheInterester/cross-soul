from utils import *
from config import LANES, Sizes, Judge, Colors, Texts, Weights, TICK_TIME, MAX_SCORE

from random import uniform
from math import log10
from dataclasses import dataclass, field

from kivy.uix.widget import Widget
from kivy.uix.label import Label
from kivy.core.window import Window
from imslib.wavesrc import WaveFile

from .audio import AudioController
from .barlines import Barlines
from .notes import NoteData
from .hud import Hud
from .notes_display import *
from .laner import Laner
from .surfer import Surfer
from .notes import TapNote, HoldNote
from .verdict import Verdicts
from data import SongInfo
from widgets.common import Placer, DrawLabel
from widgets.game import ScoreLabel


@dataclass
class Hit:
    beat: float
    """intended hit beat-time"""
    judge: Judge
    dt: float
    """actual hit offset"""

@dataclass
class Results:
    hits: list[Hit] = field(default_factory=list)
    coins: int = 0
    total_coins: int = 0
    ticks: int = 0
    total_ticks: int = 0
    weight: int = 0
    """raw score"""
    total_weight: int = 0
    max_combo: int = 0
    total_combo: int = 0

    def clear(self):
        self.hits.clear()
        self.coins = 0
        self.ticks = 0
        self.weight = 0

    def score(self):
        return MAX_SCORE * self.weight // self.total_weight

class Game(Widget):
    def __init__(
        self,
        root,
        cb,
        song_info: SongInfo,
        diff,
        preview,
    ):
        super().__init__()

        self.cb = cb
        self.preview = preview
        self.root = root

        self.now_depth = 45
        """Units from front the nowbar is located."""
        self.rate = 100 * root.settings["speed"]
        """Units between each beat."""
        self.combo = 0
        self.results = Results()
        self._ended = False

        # TODO switch difficulty and thus note data
        self.song_info = song_info
        note_data = NoteData.from_file(song_info.maps[diff])
        self.note_data = note_data
        self.ac = AudioController(
            root.mixer,
            WaveFile(song_info.audio),
            song_info.bpm,
            song_info.offset,
        )
        self.ac.set_beat(song_info.preview_start if preview else song_info.start)
        self.ac.play()
        if not preview:
            self.compute_totals()

        all_beats = (
            [coin.beat for coin in note_data.coins] +
            [tap.beat for tap in note_data.tap_notes] +
            [hold.end_beat for hold in note_data.hold_notes]
        )
        self.last_beat = max(all_beats) if all_beats else 0
        self.total_notes = note_data.total_scoreable()
        self.coins_collected = 0
        self.num_coins = len(note_data.coins)

        self.field = RenderContext(
            use_parent_modelview=True, use_parent_projection=True
        )
        self.field.shader.source = "./shaders/game.glsl"
        self.field["screen_to_space"] = root.screen_to_space
        self.field["perspective"] = root.perspective
        self.field["space_to_screen"] = root.space_to_screen

        W = Sizes.FIELD_WIDTH

        with StackFrame(self.field):
            with self.field:
                Translate(400 / 2, 0)

                # note field
                Color(0.2, 0.2, 0.4)
                Rectangle(pos=(-W/2, 0), size=(W, Sizes.FIELD_DEPTH))
                Color(a=1/8)
                for i in range(1, LANES):
                    Rectangle(pos=((i/LANES-.5) * W - Sizes.LANEDIV_THICK / 2, 0), size=(Sizes.LANEDIV_THICK, Sizes.FIELD_DEPTH))
                Color(a=1/2)
                for i in [0, LANES]:
                    Rectangle(pos=((i/LANES-.5) * W - Sizes.LANEDIV_THICK / 2, 0), size=(Sizes.LANEDIV_THICK, Sizes.FIELD_DEPTH))

                Translate(0, self.now_depth)

            # note stuff
            self.barlines = Barlines(self)
            self.field.add(self.barlines)
            self.hud = Hud(self)
            self.field.add(self.hud)
            self.notes = NotesDisplay(self, note_data)
            self.field.add(self.notes)
            self.laner_wrapper = InstructionGroup()
            self.laner = Laner(self, note_data)
            if not self.preview:
                self.laner_wrapper.add(self.laner)
            self.field.add(self.laner_wrapper)

        self.canvas.add(self.field)

        self.coins = self.notes.coin_group2
        self.canvas.add(self.coins)

        with StackFrame(self.canvas):
            with self.canvas:
                Translate(Sizes.OBSERVER[0], Sizes.OBSERVER[1])
                Scale(*(Sizes.OBSERVER[2] / (self.now_depth + Sizes.OBSERVER[2]),)*3)
                Translate(0, -Sizes.OBSERVER[1])
            self.surfer_wrapper = InstructionGroup()
            self.surfer = Surfer(self, coins=note_data.coins)
            if not self.preview:
                self.surfer_wrapper.add(self.surfer)
            self.canvas.add(self.surfer_wrapper)
            self.verdicts = Verdicts(self)
            self.canvas.add(self.verdicts)

        self.score_label = ScoreLabel(self, 0)
        self.score_label.placer.set_pos((200, 300))
        if preview:
            self.score_label.opacity = 0
        self.add_widget(self.score_label)

    def unpreview(self):
        if not self.preview:
            warn("Tried to unpreview twice!")
            return
        self.laner_wrapper.add(self.laner)
        self.surfer_wrapper.add(self.surfer)
        self.score_label.opacity = 1
        self.preview = False
        self.compute_totals()
        self.ac.gen.set_gain(1.)
        self.ac.set_beat(self.song_info.start)
        self.reset()

    def on_surf(self, pos):
        if self.preview:
            warn("Tried to interact in preview!")
            return
        t = self.ac.get_beat()
        old_pos = self.surfer.pos
        self.surfer.update_pos(t, pos)
        self.check_hit(t, old_pos)

    def on_down(self, pos):
        if self.preview:
            warn("Tried to interact in preview!")
            return
        t = self.ac.get_beat()
        self.laner.on_lane_down(t, pos)
        self.check_hit(t)

    def on_up(self, pos):
        if self.preview:
            warn("Tried to interact in preview!")
            return
        self.laner.on_lane_up(self.ac.get_beat(), pos)

    def inc_combo(self, t):
        self.combo += 1
        self.results.max_combo = max(self.results.max_combo, self.combo)

        if self.combo >= 3:
            self.hud.show2(t, f"{self.combo}", 60 + log10(self.combo) * 20)

    def drop_combo(self, t):
        self.combo = 0
        self.hud.hide2(t)

    def hit(self, note, t, judge, dt):
        self.results.hits.append(Hit(beat=note.beat, judge=judge, dt=dt))
        self.results.weight += Weights.JUDGE[judge]
        self.inc_combo(t)
        self.refresh_score(t)

        self.verdicts.issue((note.left_end + note.right_end) / 2, t, Texts.JUDGES[judge], Colors.JUDGES[judge], 30, 20)
        self.notes.on_tap_hit(note, t, judge)

    def miss(self, note, t):
        self.results.hits.append(Hit(beat=note.beat, judge=Judge.MISS, dt=0))
        self.drop_combo(t)

        self.verdicts.issue((note.left_end + note.right_end) / 2, t, Texts.JUDGES[Judge.MISS], Colors.JUDGES[Judge.MISS], 30, 20)

    def tick_hit(self, note, t, beat, pos):
        self.results.ticks += 1
        self.results.weight += Weights.TICK
        self.inc_combo(t)
        self.refresh_score(t)

        self.verdicts.issue(pos, t, Texts.TICK_HIT, Colors.TICK_HIT, 20, 15)
        self.notes.on_tick_hit(note, t, beat)

    def tick_miss(self, note, t, beat):
        self.drop_combo(t)

        self.verdicts.issue((note.left_at(beat) + note.right_at(beat)) / 2, t, Texts.TICK_MISS, Colors.TICK_MISS, 20, 15)
        self.notes.on_tick_miss(note, t, beat)

    def coin_collect(self, coin, t):
        self.results.coins += 1
        self.results.weight += Weights.COIN
        self.inc_combo(t)
        self.refresh_score(t)

        self.verdicts.issue(coin.position, t, Texts.COIN_COLLECT, Colors.COIN_COLLECT, 35, 15)
        self.notes.on_coin_collect(coin, self.ac.get_beat())

    def coin_miss(self, coin, t):
        self.drop_combo(t)

        self.verdicts.issue(coin.position, t, Texts.COIN_MISS, Colors.COIN_MISS, 35, 15)

    def compute_totals(self):
        coins = len(self.note_data.coins)
        taps = len(self.note_data.tap_notes)
        ticks = 0
        for note in self.note_data.hold_notes:
            # TODO deduplicate with Laner on_update
            ticks += max(0, int((note.end_beat - note.start_beat) / self.ac.bps / TICK_TIME) - 1)
        weight = coins * Weights.COIN + len(self.note_data.tap_notes) * Weights.JUDGE[Judge.PERFECT] + ticks * Weights.TICK
        self.results.total_coins = coins
        self.results.total_ticks = ticks
        self.results.total_weight = weight
        self.results.total_combo = coins + ticks + taps

    def refresh_score(self, t=None):
        self.score_label.set_score(t, self.results.score())

    def check_hit(self, t, old_pos=None):
        pos = self.surfer.pos
        if old_pos is None:
            old_pos = pos
        lpos, rpos = sorted([pos, old_pos])
        for i, held in enumerate(self.laner.lane_state):
            if held:
                if intersect(i / LANES, (i + 1) / LANES, lpos, rpos):
                    self.on_hit(t, i)

    def on_hit(self, t, lane):
        self.surfer.on_hit(t)
        self.laner.on_lane_hit(t, lane)

    def reset(self):
        self.results.clear()
        self.barlines.reset()
        self.verdicts.clear()
        self.notes.reset()
        self.laner.reset()
        self.surfer.reset()

    def refresh(self):
        rate = 100 * self.root.settings["speed"]
        if self.rate != rate:
            self.rate = rate
            self.notes.recalculate()
        t = self.ac.get_beat()
        if self.preview:
            end = self.song_info.preview_start + self.song_info.preview_len
            if t > end:
                self.ac.set_beat(self.song_info.preview_start)
                self.reset()
                return
            self.ac.gen.set_gain(slide(t, end-self.ac.bps, end)(1, 0))
        self.barlines.refresh(t)
        self.notes.refresh(t)
        if not self.preview:
            self.laner.on_update(t)
            self.surfer.on_update(t)
            self.check_hit(t)
        self.hud.refresh(t)
        self.verdicts.refresh(t)
        self.score_label.refresh(t)
        if not self.preview and not self._ended and self.ac.get_beat() > self.last_beat + 4:
            self._ended = True
            if self.cb:
                self.cb(self.results)
            else:
                warn("Game ended with no callback!")
