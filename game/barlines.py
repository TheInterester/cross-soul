from utils import *
from kivy.graphics.texture import Texture
from random import random
from config import Sizes

class Barline(InstructionGroup):
    def __init__(self, game, beat, alpha, text):
        super().__init__()

        self.beat = beat
        self.game = game
        self.alpha = alpha

        T = Sizes.BARLINE_THICK
        W = Sizes.FIELD_WIDTH

        with StackFrame(self):
            self.trans = Translate()
            self.add(self.trans)

            self.color = Color()
            self.add(self.color)
            self.add(Rectangle(pos = (-W/2, -T/2), size = (W, T)))
            self.add(label(text, "Regular", (1,.5), (-W/2-2,0), 20))
            self.add(label(text, "Regular", (0,.5), (W/2+2,0), 20))

    def refresh(self, t):
        t -= self.beat
        self.color.a = self.alpha if t < 0 else .5 * clamp(0, 1, 1-t)
        self.trans.xy = (0, -min(0, t) * self.game.rate)
        return t > 1

class Barlines(InstructionGroup):
    def __init__(self, game):
        super().__init__()

        self.game = game
        self.next = 0

    def reset(self):
        self.next = 0
        self.clear()

    def refresh(self, t):
        while self.next <= t + Sizes.FIELD_DEPTH / self.game.rate:
            measure = self.next % 4 == 0
            text = f"{self.next//4+1}" if measure else ""
            self.add(Barline(self.game, self.next, 1/2 if measure else 1/8, text))
            self.next += 1

        for barline in self.children:
            if barline.refresh(t):
                self.remove(barline)
