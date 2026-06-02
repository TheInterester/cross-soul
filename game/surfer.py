from utils import *
from .notes import NoteData
from .audio import AudioController
from imslib.leap_ims import LeapInterface
from kivy.core.window import Window
from imslib.leap_ims import LeapInterface
from kivy.clock import Clock as kivyClock
from config import LANES, Sizes, Judge, HITSTUN

# Constants
SURFER_HEIGHT = 0.3
SURFER_COLLECT_RADIUS = 1 / LANES  # normalized x fraction
SLOP_WINDOW = Judge.PERFECT.value  # seconds

kLeapRange = ((-150, 150), (100, 500), (-200, 250))


class Surfer(InstructionGroup):
    def __init__(
        self,
        game,
        coins,
    ):
        super().__init__()
        self.pos = 0
        self.game = game
        # sorted list of Coin data objects
        self.coins = sorted(coins, key=lambda c: c.beat)
        self.past_coins = set()
        self.idx = 0

        self.hitstun = None

        W = Sizes.COIN_SIZE
        T = 5

        with StackFrame(self):
            self.trans = Translate()
            self.add(self.trans)
            self.add(Translate(0, Sizes.COIN_SIZE))
            self.color = Color(hsv=(.15, 1, 1), a=.5)
            self.add(self.color)
            self.add(BoxShadow(pos=(-W/2-T/2, -W/2-T/2), size=(W+T, W+T), inset=True))
            self.add(Line(rectangle=(-W/2-T/2, -W/2-T/2, W+T, W+T), width=T/2, joint="miter"))
            self.add(Rectangle(pos=(-W/2-T,-Sizes.COIN_SIZE), size=(W+T*2, Sizes.COIN_SIZE-W/2-T)))

    def reset(self):
        self.past_coins.clear()
        self.idx = 0

    def update_pos(self, t, pos):
        self.pos = pos
        self.trans.x = (pos - .5) * Sizes.FIELD_WIDTH
        self.on_update(t)

    def on_update(self, t):
        if self.hitstun is not None:
            if t - self.hitstun >= HITSTUN * self.game.ac.bps:
                self.hitstun = None
                self.color.a = .5

        for i in range(self.idx, len(self.coins)):
            if i in self.past_coins:
                continue
            coin = self.coins[i]
            diff = (t - coin.beat) / self.game.ac.bps
            # TODO delay collection, maybe have precision judgements
            if diff < -SLOP_WINDOW:
                break
            if diff > SLOP_WINDOW:
                self.game.coin_miss(coin, t)
                self.past_coins.add(i)
                continue
            # within timing window - check horizontal position
            if abs(self.pos - coin.position) <= SURFER_COLLECT_RADIUS and self.hitstun is None:
                self.game.coin_collect(coin, t)
                self.past_coins.add(i)

        while self.idx < len(self.coins) and self.idx in self.past_coins:
            self.idx += 1

    def on_hit(self, t):
        self.color.a = 0.2
        self.hitstun = t
