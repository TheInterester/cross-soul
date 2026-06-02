from utils import *
from config import Colors, Texts
from widgets.common import TransPlacer, Placer
from widgets.song_related import Card, Board, Selector
from widgets.confirm import SpeedControl, DifficultyControl, Loop2
from game.game import Game

class ConfirmMenu(RelativeLayout):
    def __init__(self, root, selector: TransPlacer[TransPlacer[Selector]], board: TransPlacer[Board], card: TransPlacer[Card]):
        super().__init__()

        self.t = 1
        self.phase = Phase.ENTER
        self.controlling = False

        self.j = 0
        self.vj = self.j

        self.game = Game(root, cb=None, song_info=card.widget.info, diff=root.settings["difficulty"], preview=True)
        self.add_widget(self.game)

        self.selector = selector
        self.selector.widget.widget.size = 70, 30
        self.selector.set_pos((200, 300-80/2))
        self.selector.set_angle(0)
        self.selector.widget.widget.color = Colors.LAVENDER.rgba
        self.add_widget(self.selector)

        self.loop = Placer(Loop2())
        self.loop.widget.size = 360, 80
        self.loop.widget.radius = 15
        self.loop.set_pos((200 - self.loop.widget.width/2, 300 - self.loop.widget.height/2))
        self.loop.widget.refresh()

        self.upper = Placer(self.loop)
        self.add_widget(self.upper)

        self.lower = Placer(RelativeLayout())

        self.diff = Placer(DifficultyControl(card.widget.info.levels))
        self.diff.set_pos((200, 50))
        self.lower.widget.add_widget(self.diff)

        self.speed = Placer(SpeedControl())
        self.speed.widget.opacity = 0
        self.speed.set_pos((200, 50))
        self.lower.widget.add_widget(self.speed)

        self.add_widget(self.lower)
        self.controls = [self.diff, self.speed, None, None]

        self.closer = Placer(Placer(RelativeLayout()))
        self.closer.set_pos((200, 150))
        self.closer.widget.set_pos((-200, -150))

        self.board = board
        self.board.set_pos((200 - 360*1.5/4, 160))
        self.board.set_angle(90)
        self.closer.widget.widget.add_widget(self.board)

        self.card = card
        self.card.set_pos((200 + 360*1.5/4, 160))
        self.closer.widget.widget.add_widget(self.card)

        self.add_widget(self.closer)

        self.root = root
        self._setup(0, False)
        self.root.rangers.disable("back")

    def _setup(self, i, fast=True):
        match i:
            case 0:
                self.root.rangers.setup([
                    (2, "back", self._go_back),
                    (1, None, None),
                    *((2, Texts.DIFF_NAMES[i], functools.partial(lambda i: self._change_diff(i), i)) for i in range(4)),
                    (1, None, None),
                    (2, "play!", self._play)
                ], fast)
                self.root.rangers.disable("play!")
            case 1:
                self.root.rangers.setup([
                    (2, "back", self._go_back),
                    (1, None, None),
                    (2, "−−", lambda: self._change_speed(-1)),
                    (2, "−", lambda: self._change_speed(-.1)),
                    (2, "+", lambda: self._change_speed(.1)),
                    (2, "++", lambda: self._change_speed(1)),
                    (1, None, None),
                    (2, "play!", self._play),
                ], fast)
                self.root.rangers.disable("play!")
            case 2:
                self.root.rangers.setup([
                    (2, "back", self._go_back),
                    (10, None, None),
                    (2, "play!", self._play),
                ], fast)
                self.root.rangers.disable("play!")
            case 3:
                self.root.rangers.setup([
                    (2, "back", self._go_back),
                    (10, None, None),
                    (2, "play!", self._play),
                ], fast)
                if self.phase == Phase.ENTER:
                    self.root.rangers.disable("play!")

    def _change_speed(self, delta):
        self.root.settings["speed"] = clamp(1, 10, self.root.settings["speed"] + delta)

    def _change_diff(self, diff):
        if self.card.widget.info.levels[diff] is None:
            return
        self.root.settings["difficulty"] = diff

    def _play(self):
        if self.phase != Phase.STAY:
            return
        chart_data = self.card.widget.info.maps[self.root.settings["difficulty"]]
        if chart_data == "-":
            warn("Map does not exist!")
            return
        self.controlling = True
        self.phase = Phase.EXIT
        self.remove_widget(self.game)
        self.root.transition("game", self.game)

    def _go_back(self):
        if self.phase != Phase.STAY:
            return
        self.phase = Phase.EXIT
        self.remove_widget(self.game)
        # TODO integrate with hypothetical selection screen preview
        self.game.ac.kill()
        self.selector.snapshot()
        self.selector.widget.snapshot()
        self.remove_widget(self.selector)
        self.board.snapshot()
        self.closer.widget.widget.remove_widget(self.board)
        self.card.snapshot()
        self.closer.widget.widget.remove_widget(self.card)
        self.root.transition("select", self.selector, self.board, self.card)

    def on_surf(self, pos):
        j = self.j
        self.j = min(3, math.floor(pos * 4))
        if j != self.j:
            self._switch(j, self.j)

    def _switch(self, fro, to):
        f = self.controls[fro]
        if f is not None:
            f.widget.opacity = 0
        t = self.controls[to]
        if t is not None:
            t.widget.opacity = 1
        self._setup(to)

    def _refresh(self):
        self.selector.widget.set_pos((((.5 + self.vj) / 4 - .5) * 360, 0))
        speed = f"{self.root.settings['speed']:.2f}"
        diff = self.root.settings["difficulty"]
        self.loop.widget.setts[0].info = Texts.DIFF_NAMES[diff]
        self.loop.widget.setts[0].color = Colors.DIFFS[diff].rgba
        for i, diff in enumerate(self.diff.widget.diffs):
            if diff is not None:
                diff.opacity = 1 if i == self.root.settings["difficulty"] else .5
        self.loop.widget.setts[1].info = speed
        self.speed.widget.text = speed

    def update(self, dt):
        self.game.refresh()
        self.t += dt * self.phase * 2
        if self.phase == Phase.ENTER:
            self.root.rangers.disable("back")
        if self.t <= 0:
            self.t = 0
            self.phase = Phase.STAY
            self.root.rangers.enable("back")
            if self.j == 3:
                self.root.rangers.enable("play!") # kinda hacky, whatever
        self.upper.set_pos((0, self.t * 100))
        self.upper.opacity = slide(self.t, .5, 1)(1, 0)
        self.lower.set_pos((0, self.t * -150))
        self.lower.opacity = slide(self.t, .5, 1)(1, 0)
        if self.controlling:
            self.closer.set_scale(1 + 2 * self.t ** 3)
            self.closer.opacity = slide(self.t, .5, 1)(1, 0)
        if self.phase != Phase.EXIT:
            self.vj = lerp(self.j, self.vj, .7 ** (dt * 60))
            self._refresh()
        return self.t > 1
