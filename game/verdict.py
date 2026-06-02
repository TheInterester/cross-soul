from utils import *
from config import Sizes

class Verdict(InstructionGroup):
    def __init__(self, pos, t, text, color, height, size):
        super().__init__()

        self.t = t

        h, s, v = color.hsv

        with StackFrame(self):
            self.add(Translate(Sizes.FIELD_WIDTH * (pos - .5), height))
            self.translate = Translate()
            self.add(self.translate)
            self.color = Color(hsv=(h, s/2, v))
            self.add(self.color)
            self.add(label(text, "Bold", (.5,0), (0,0), size, outline_width=size, outline_color=Color(hsv=(h, s/2, v/2)).rgba))

    def refresh(self, t):
        t -= self.t
        self.translate.y = slide(t, 0, .3)(0, 10)
        self.color.a = slide(t, 0, .3)(1, 0)
        return t > 1

class Verdicts(InstructionGroup):
    def __init__(self, game):
        super().__init__()
        self.game = game

    def issue(self, pos, t, text, color, height, size):
        t /= self.game.ac.bps
        v = Verdict(pos, t, text, color, height, size)
        self.add(v)

    def refresh(self, t):
        t /= self.game.ac.bps
        for v in [*self.children]:
            if v.refresh(t):
                self.remove(v)
