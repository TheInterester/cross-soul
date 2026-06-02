from utils import *
from widgets.common import Placer
from game.game import Game

class GameMenu(RelativeLayout):
    def __init__(self, root, game: Game):
        super().__init__()

        self.t = 0
        self.phase = Phase.STAY

        self.game = game
        self.game.cb = self._go_results
        self.game.unpreview()
        self.wrapper = Placer(self.game)
        self.add_widget(self.wrapper)

        self.root = root
        self.root.rangers.setup([])
        self.root.rangers.lights.opacity = 0

    def _go_results(self, results):
        if self.phase != Phase.STAY:
            return
        self.phase = Phase.EXIT
        self.root.transition("results", results, self.game.song_info, self.game.ac)

    def on_surf(self, pos):
        self.game.on_surf(pos)

    def on_down(self, pos):
        self.game.on_down(pos)

    def on_up(self, pos):
        self.game.on_up(pos)

    def _change_speed(self, delta):
        self.root.settings["speed"] = clamp(1, 10, self.root.settings["speed"] + delta)

    def on_key_down(self, keycode, modifiers):
        # dev keys!
        jump = (4 if "shift" in modifiers else 1) * (
            4 if "ctrl" not in modifiers else 1
        )
        sprint = 10 if "shift" in modifiers else 1
        match keycode[1]:
            case "down":
                self.game.ac.toggle()
            case "left":
                self.game.ac.scrub(-jump)
                self.game.reset()
            case "right":
                self.game.ac.scrub(jump)
            case ",":
                self._change_speed(-.1 * sprint)
            case ".":
                self._change_speed(.1 * sprint)

    def update(self, dt):
        self.game.refresh()
        self.t += dt * self.phase * 2
        self.wrapper.set_pos((0, self.t**2 * -400))
