from utils import *
import config as cfg

class SurferInput:
    """Source of surfer input information."""

    # TODO leap pos
    def __init__(self, cb):
        super().__init__()
        self.cb = cb
        self.pos = 0
        Window.bind(mouse_pos=self.on_mouse_pos)

    def on_pos(self, pos):
        self.pos = clamp(0, 1, pos)
        self.cb(self.pos)

    def on_mouse_pos(self, win, pos):
        self.on_pos(pos[0] / win.width)

class LanerInput:
    """Source of laner input information."""
    I_KEY = invert(cfg.LANER_KEYS)

    #TODO leap pos
    def __init__(self, on_down, on_up):
        super().__init__()
        self.on_down = on_down
        self.on_up = on_up

    def on_pos(self, pos):
        self.cb(clamp(0, 1, pos))

    def on_key_down(self, keycode):
        i = self.I_KEY.get(keycode[1])
        if i is None or self.on_down is None:
            return
        self.on_down(i)

    def on_key_up(self, keycode):
        i = self.I_KEY.get(keycode[1])
        if i is None or self.on_up is None:
            return
        self.on_up(i)
