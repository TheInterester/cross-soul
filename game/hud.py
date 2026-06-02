from utils import *

class Hud(InstructionGroup):
    def __init__(self, game):
        super().__init__()

        self.game = game
        self.t2 = None
        """combo activation time"""
        self.s2 = None
        """combo break time"""

        with StackFrame(self):
            self.translate2 = Translate()
            self.add(self.translate2)
            self.scale2 = Scale()
            self.add(self.scale2)
            self.rotate2 = Rotate()
            self.add(self.rotate2)

            self.color2 = Color(hsv=(0,0,1))
            self.add(self.color2)
            self.combo = InstructionGroup()
            self.add(self.combo)

    def show2(self, t, text, size):
        t /= self.game.ac.bps
        self.combo.clear()
        self.s2 = None
        self.t2 = t
        self.combo.add(label(text, "Bold", (.5,.5), (0,0), size, outline_width=size, outline_color=Color(hsv=(0,0,.5)).rgb))

    def hide2(self, t):
        t /= self.game.ac.bps
        if self.s2 is not None:
            return
        self.s2 = t

    def refresh(self, t):
        t /= self.game.ac.bps
        t2 = t

        if self.t2 is not None:
            s2 = 0 if self.s2 is None else t2 - self.s2
            t2 -= self.t2
            self.color2.a = slide(s2, 0, .5, lambda x: 1-(1-x)**4)(.5, 0)
            self.scale2.xyz = (slide(t2, 0, .1)(1.2, 1),) * 3
            self.translate2.y = 400 + slide(s2, 0, .5, lambda x: x**2)(0, -100)
            self.rotate2.angle = slide(s2, 0, .5)(0, -90)
