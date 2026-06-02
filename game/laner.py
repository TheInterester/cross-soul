from utils import *
from .audio import AudioController
from .notes import NoteData
from fractions import Fraction
from config import LANES, LANER_KEYS, Sizes, Judge, TICK_TIME, Colors, HITSTUN

SLOP_WINDOW = Judge.BAD.value  # seconds (matches Judge.BAD)

def _lane_pos(lane):
    return (lane + 0.5) / LANES

def _covers_lane(left, right, lane):
    # TODO the eps is a hack
    return intersect(left + .1/LANES, right - .1/LANES, lane / LANES, (lane + 1) / LANES)

def _judge(abs_diff):
    for j in (Judge.PERFECT, Judge.FANTASTIC, Judge.GREAT, Judge.OKAY, Judge.BAD):
        if abs_diff <= j.value:
            return j
    return Judge.MISS

class _ActiveHold:
    def __init__(self, note):
        self.note      = note
        self.released  = False
        self.next_tick = 1  # 1-based, matches TickDisplay


class Laner(InstructionGroup):
    def __init__(self, game, note_data):
        super().__init__()
        self.game             = game
        self.lane_state       = [False] * LANES
        self.lane_release = [None] * LANES
        self.lane_hit = [None] * LANES
        self._taps         = []
        self._holds        = []
        self._next_tap     = 0
        self._next_hold    = 0  # for auto-spawning active holds
        self._hit_taps     = set()
        self._active_holds = []
        self.hitstun = None
        """we only hitstun ticks, IDK if that makes the most sense"""

        # nowbar: one colored segment per lane

        #laser visual
        LASER_HEIGHT = 1500
        self._laser_color_targets = []
        self._laser_colors = []
        width = Sizes.FIELD_WIDTH / LANES * 1
        for i in range(LANES):
            cx = Sizes.FIELD_WIDTH * ((i + .5) / LANES - .5)
            c = Color()
            self.add(c)
            self.add(Rectangle(pos=(cx-width/2,-self.game.now_depth), size=(width,LASER_HEIGHT), texture=gradient))
            self._laser_color_targets.append(Color())
            self._laser_colors.append(c)

        self._taps  = sorted(note_data.tap_notes,  key=lambda n: n.beat)
        self._holds = sorted(note_data.hold_notes, key=lambda n: n.start_beat)

    def reset(self):
        self._next_tap = 0
        self._next_hold = 0
        self._hit_taps.clear()
        self._active_holds.clear()

    def on_lane_down(self, t, lane):
        if self.lane_state[lane]:
            warn(f"lane {lane} re-pressed, watch out")
        self.lane_state[lane] = True
        self._laser_color_targets[lane].rgba = Color().rgba

        bps = self.game.ac.bps

        for i in range(self._next_tap, len(self._taps)):
            if i in self._hit_taps:
                continue
            note = self._taps[i]
            diff = (t - float(note.beat)) / bps
            if diff < -SLOP_WINDOW:
                break
            if diff >  SLOP_WINDOW:
                continue
            if _covers_lane(note.left_end, note.right_end, lane):
                self._hit_taps.add(i)
                j = _judge(abs(diff))
                self._laser_color_targets[lane].rgba = Colors.JUDGES[j].rgba
                self.game.hit(note, t, j, diff)
                break

    def on_lane_up(self, _t, lane):
        if not self.lane_state[lane]:
            warn(f"lane {lane} un-pressed twice, watch out")
        self.lane_state[lane] = False
        self.lane_release[lane] = _t

    def on_lane_hit(self, t, lane):
        self.lane_hit[lane] = t
        self.hitstun = t

    def on_update(self, t):
        bps = self.game.ac.bps

        if self.hitstun is not None:
            if t - self.hitstun >= HITSTUN * bps:
                self.hitstun = None

        # advance _next_tap and miss notes
        while self._next_tap < len(self._taps):
            if self._next_tap in self._hit_taps:
                self._next_tap += 1
                continue
            note = self._taps[self._next_tap]
            if (t - float(note.beat)) / bps <= SLOP_WINDOW:
                break
            self.game.miss(note, t)
            self._next_tap += 1

        # auto-spawn holds as their start beat arrives
        while self._next_hold < len(self._holds):
            note = self._holds[self._next_hold]
            if float(note.start_beat) > t:
                break
            self._active_holds.append(_ActiveHold(note))
            self._next_hold += 1

        # score each tick independently based on current lane state
        for ah in self._active_holds:
            note = ah.note
            # only have a tick if there's still TICK_TIME until the end, for leniency
            while ah.next_tick + 1 <= (note.end_beat - note.start_beat) / bps / TICK_TIME:
                tick_beat = note.start_beat + ah.next_tick * TICK_TIME * bps
                if float(tick_beat) > t:
                    break
                left, right = note.left_at(tick_beat), note.right_at(tick_beat)
                lane = next((i for i in range(LANES) if self.lane_state[i] and _covers_lane(left, right, i)), None)
                if not self.hitstun and lane is not None:
                    self.game.tick_hit(note, t, tick_beat, _lane_pos(lane))
                else:
                    self.game.tick_miss(note, t, tick_beat)
                ah.next_tick += 1

        # update laser visual
        for i, c in enumerate(self._laser_colors):
            c.rgba = self._laser_color_targets[i].rgba
            if self.lane_state[i]:
                c.a = 0.4
            elif self.lane_release[i] is not None:
                c.a = slide(t - self.lane_release[i], 0, 0.5)(0.4, 0)
                if t - self.lane_release[i] > 0.5:
                    self.lane_release[i] = None
            else:
                c.a = 0
            if self.hitstun is not None:
                c.a *= .3
            if self.lane_hit[i] is not None:
                c.rgba = slide(t - self.lane_hit[i], 0, 1)((1,.2,.2,.9), c.rgba)
                if t - self.lane_hit[i] > 1:
                    self.lane_hit[i] = None

        # prune active holds
        self._active_holds = [ah for ah in self._active_holds if float(ah.note.end_beat) > t]
