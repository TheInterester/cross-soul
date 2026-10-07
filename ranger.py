from utils import *
import config as cfg

Builder.load_string("""
#: import C config.Colors
#: import utils utils

<Light>:
    size_hint: None, None
    canvas:
        Color
        Rectangle:
            pos: self.gap/2, 0
            size: self.width - self.gap, self.height
            texture: utils.gradient

<Ranger>:
    size_hint: None, None
    opacity: 0 if not self.released else .5 if self._disabled else 1
    canvas:
        Color:
            rgba: C.HOTPINK.rgba if self.active else C.PINK.rgba
        RoundedRectangle:
            pos: self.gap/2, -self.radius - (self.bob + self.fall) * self.height
            size: self.width - self.gap, self.height+self.radius
            radius: [(self.radius, self.radius)]
    DrawLabel:
        pos: self.parent.width/2, self.parent.height * (1/2 - (self.parent.bob + self.parent.fall))
        text: self.parent.label
        variant: "Bold"
        font_size: self.parent.font_size
        color: C.WHITE.rgba
        kwargs: {} if self.parent._disabled else { "outline_width": self.parent.font_size, "outline_color": C.HOTPINK.rgba }
""")

class Light(RelativeLayout):
    """Indicates that a key is pressed."""
    gap = NumericProperty(10)

setup_time = .15
"""time to set-down and time to setup, so total time is double this"""

class Ranger(RelativeLayout):
    """Indicates a range of keys for an action."""
    def __init__(self, cb):
        super().__init__()
        self.cb = cb

    def update(self, dt):
        if self.released:
            self.fall = max(0, self.fall - dt / setup_time)
        self.bob = lerp(1/8 if self.active else 0, self.bob, .7 ** (dt * 60))

    def downdate(self, dt):
        self.fall += dt / setup_time

    _disabled = BooleanProperty(False)
    """whether it's set to not be interactible"""
    released = BooleanProperty(False)
    """whether it's allowed to move up (after the old ones move out of the way)"""
    active = BooleanProperty(False)
    """whether it's pressed"""
    gap = NumericProperty(10)
    """distance between adjacent Rangers"""
    radius = NumericProperty(5)
    label = StringProperty("?")
    font_size = NumericProperty(15)
    bob = NumericProperty(0)
    """displacement due to being pressed"""
    fall = NumericProperty(1)
    """displacement due to transition in/out"""

class Rangers(RelativeLayout):
    WIDTH = 400 / cfg.LANES

    def __init__(self):
        super().__init__()
        self.lights = RelativeLayout()
        self.add_widget(self.lights)
        self.ls = []
        for i in range(cfg.LANES):
            l = Light()
            l.pos = self.WIDTH * i, 0
            l.size = self.WIDTH, 40
            l.opacity = 0
            self.lights.add_widget(l)
            self.ls.append(l)
        self.old_rs = []
        self.rs: list[Ranger] = []
        """list of ranges"""
        self.idxs = [None] * cfg.LANES
        """mapping from key to range"""
        self.states = [False] * cfg.LANES
        """whether a key is pressed (to reset on re-setup)"""
        self.setup([])

    def setup(self, ranges: list[tuple[int, str, Callable[[], None]]], fast=False):
        if fast:
            if self.t is None:
                self.t = setup_time
            released = self.rs[0].released if len(self.rs) != 0 else 0
            fall = self.rs[0].fall if len(self.rs) != 0 else 0
            for r in self.rs:
                self.remove_widget(r)
        else:
            self.t = 0 if len(self.rs) != 0 else setup_time
            if len(self.old_rs) != 0:
                warn("Old rangers didn't have time to disappear!")
            for r in self.old_rs:
                self.remove_widget(r)
            self.old_rs = self.rs
        self.rs = []
        self.cts = []
        """number of keys in each range currently pressed"""
        for i in range(cfg.LANES):
            self.idxs[i] = None
            self.states[i] = False
        i = 0
        idx = 0
        for w, label, cb in ranges:
            if cb is not None:
                r = Ranger(cb)
                r.pos = self.WIDTH * i, 0
                r.size = self.WIDTH * w, 20
                r.label = label
                if fast:
                    r.released = released
                    r.fall = fall
                self.add_widget(r)
                self.rs.append(r)
                self.cts.append(0)
                for j in range(w):
                    self.idxs[i+j] = idx
                idx += 1
            i += w
        if i != cfg.LANES and i != 0:
            warn(f"Ranger setup only given {i} lanes!")

    def disable(self, label):
        idx = next(i for i, r in enumerate(self.rs) if r.label == label)
        self.rs[idx]._disabled = True

    def enable(self, label):
        idx = next(i for i, r in enumerate(self.rs) if r.label == label)
        self.rs[idx]._disabled = False

    def on_down(self, pos):
        self.ls[pos].opacity = 1
        if self.states[pos]:
            return
        self.states[pos] = True
        idx = self.idxs[pos]
        if idx is None:
            return
        self.cts[idx] += 1
        if self.cts[idx] != 1:
            return
        r = self.rs[idx]
        if r._disabled:
            return
        r.active = True
        r.cb()

    def on_up(self, pos):
        self.ls[pos].opacity = 0
        if not self.states[pos]:
            return
        self.states[pos] = False
        idx = self.idxs[pos]
        if idx is None:
            return
        self.cts[idx] -= 1
        if self.cts[idx] != 0:
            return
        r = self.rs[idx]
        r.active = False

    def update(self, dt):
        if self.t is not None:
            self.t += dt
            for r in self.old_rs:
                r.downdate(dt)
            if setup_time <= self.t:
                self.t = None
                for r in self.old_rs:
                    self.remove_widget(r)
                self.old_rs = []
                for r in self.rs:
                    r.released = True
        for r in self.rs:
            r.update(dt)
