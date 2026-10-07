from utils import *

import numpy as np

from config import Judge, Colors

from imslib.wavesrc import WaveFile
from imslib.wavegen import WaveGenerator

from enum import Enum

# ScratchSting.wav by Psykoosiossi -- https://freesound.org/s/345831/ -- License: Attribution 3.0
w_select = WaveFile("./assets/select.wav")

# Button Tick by NenadSimic -- https://freesound.org/s/268108/ -- License: Creative Commons 0
w_navigate = WaveFile("./assets/navigate.wav")

# SCORE COUNT.wav by xtrgamr -- https://freesound.org/s/253546/ -- License: Attribution 4.0
w_tally = WaveFile("./assets/tally.wav")

# Whoosh Simpler by original_sound -- https://freesound.org/s/364660/ -- License: Attribution 3.0
w_whoosh = WaveFile("./assets/whoosh.wav")

class State(Enum):
    WAIT = 0
    STARTING = 1
    GAME = 2
    ENDING = 3
    RESULTS = 4
    RETURNING = 5

thresholds = [
    (1_200_000, "SSS", Judge.PERFECT),
    (1_100_000, "SS+", Judge.PERFECT),
    (1_000_000, "SS", Judge.PERFECT),
    (900_000, "S+", Judge.FANTASTIC),
    (800_000, "S", Judge.FANTASTIC),
    (700_000, "A+", Judge.GREAT),
    (600_000, "A", Judge.GREAT),
    (500_000, "B+", Judge.OKAY),
    (400_000, "B", Judge.OKAY),
    (300_000, "C+", Judge.BAD),
    (200_000, "C", Judge.BAD),
    (100_000, "D+", Judge.MISS),
    (0, "D", Judge.MISS),
]

# time from start of results transition to tallying beginning
wait = .2
# time the tallying takes
compute = 5.

class Card(InstructionGroup):
    def __init__(self, mixer, metadata=None):
        super().__init__()

        self.state = State.WAIT
        self.select = 0
        self.t = 0
        self.mixer = mixer
        self.cb = None

        self.results = None
        self.i = None # next result to process
        self.scor = None
        self.count = {}

        self.tally = None # loop gen handle

        with StackFrame(self):
            self.add(Scale(1,1,0))
            self.add(Translate(60, 60))
            self.rotate = Rotate(axis=(0,1,0))
            self.add(self.rotate)
            self.add(Translate(-60, -60))

            # base box
            self.add(Color(hsv=(0,0,0), a=.5))
            self.box = Rectangle()
            self.add(self.box)

            self.add(Color())
            self.hint = InstructionGroup()
            self.add(self.hint)

            self.stats = InstructionGroup()
            self.add(self.stats)

            # jacket
            self.frame = Rectangle()
            with Stencil(self, self.frame):
                self.add(Color())
                self.jacket = Rectangle(source=metadata["jacket"])
                self.add(self.jacket)

                self.darken = Color(hsv=(0,0,0), a=0)
                self.add(self.darken)
                self.add(Rectangle(pos=(0,0), size=(120,120)))

            # text
            self.add(Translate(48, 60))

            self.translate = Translate()
            self.add(self.translate)
            self.orient = Rotate()
            self.add(self.orient)

            self.lighten = Color(hsv=(0,0,1))
            self.add(self.lighten)
            self.add(label(metadata["artist"].upper(), "Regular", (0,0), (0,5), 5))
            self.add(label(metadata["title"].upper(), "Bold", (0,.5), (0,0), 10))
            self.difficulty = InstructionGroup()
            self.difficulty.add(label("EASY", "Regular", (0,1), (0,-5), 5))
            self.add(self.difficulty)

        self.stat = InstructionGroup()

        with StackFrame(self.stat):

            self.stat.add(Translate(15,15))

            with StackFrame(self.stat):
                self.stat.add(Translate(0,50))
                self.stat.add(Color(a=.25))
                self.stat.add(label("0000000", "Bold", (1,.5), (75,0), 10))
                self.stat.add(Color())
                self.stat.add(label("SCORE", "Regular", (1,.5), (30,0), 6))
                self.score = InstructionGroup()
                self.stat.add(self.score)
                self.stat.add(Translate(0,-9))
                self.stat.add(Color(1, 0.85, 0, 0.25))
                self.stat.add(label("000/000", "Bold", (1,.5), (75,0), 10))
                self.stat.add(Color(1, 0.85, 0))
                self.stat.add(label("COINS", "Regular", (1,.5), (30,0), 6))

                self.coin_count = InstructionGroup()
                self.stat.add(self.coin_count)
                self.stat.add(Translate(0,-5))
                self.counts = {}
                for judge in Judge:
                    self.stat.add(Translate(0,-7))
                    self.stat.add(Color(hsv=hsv_judge[judge], a=.25))
                    self.stat.add(label("000", "Bold", (1,.5), (29,0), 6))
                    self.stat.add(Color(hsv=hsv_judge[judge]))
                    self.stat.add(label(text_judge[judge], "Regular", (1,.5), (17,0), 4))
                    self.counts[judge] = InstructionGroup()
                    self.stat.add(self.counts[judge])


            self.stat.add(Translate(35,12))
            self.stat.add(Color(a=.25))
            self.stat.add(Line(
                points=[0,0,55,0],
                width=.2,
                cap="square",
            ))
            self.stat.add(Line(
                points=[0,-20,0,20,55,20,55,-20],
                width=.2,
                joint="miter",
                close=True,
            ))
            self.stat.add(label("EARLY", "Regular", (0,0), (1,-20), 5))
            self.stat.add(label("LATE", "Regular", (0,1), (1,20), 5))
            self.dots = InstructionGroup()
            self.stat.add(self.dots)

        with StackFrame(self.stat):
            self.stat.add(Translate(102,66))
            self.rscale = Scale()
            self.stat.add(self.rscale)
            self.stat.add(Rotate(angle=-20))
            self.rcolor = Color()
            self.stat.add(self.rcolor)
            self.rank = InstructionGroup()
            self.stat.add(self.rank)

        self.refresh()

    # play a sound-fx
    def play_sfx(self, file, gain=1, loop=False):
        gen = WaveGenerator(file, loop)
        gen.set_gain(gain)
        self.mixer.add(gen)
        return gen

    def switch(self):
        if self.state != State.WAIT:
            return
        self.select = (self.select + 1) % 2
        self.jacket.source = "./assets/shiawase.jpg" if self.select == 1 else "./assets/shiawase day.jpg"
        self.difficulty.clear()
        self.difficulty.add(label("HARD" if self.select == 1 else "EASY", "Regular", (0,1), (0,-5), 5))
        self.play_sfx(w_navigate,4)

    def begin_game(self, cb):
        if self.state != State.WAIT:
            return
        self.state = State.STARTING
        self.t = 0
        self.cb = cb
        self.play_sfx(w_select, 1.5)

    def end_game(self, results, coin_stats=(0, 0),final_score = 0):
        if self.state != State.GAME:
            return
        self.state = State.ENDING
        self.t = 0
        self.results = results
        self.coins_collected, self.num_coins = coin_stats
        dts = [dt for _, _, dt, _ in results]
        print("mean", np.mean(dts), "std", np.std(dts))
        self.i = 0
        self.scor = final_score
        self.dots.clear()
        self.coin_count.clear()
        for judge in Judge:
            self.count[judge] = 0
        self.stats.add(self.stat)

    def restore(self):
        if self.state != State.RESULTS:
            return
        self.state = State.RETURNING
        self.t = 0
        self.stats.remove(self.stat)
        self.play_sfx(w_navigate,4)

    def refresh(self):
        self.hint.clear()
        match self.state:
            case State.WAIT | State.STARTING | State.GAME:
                if self.state == State.WAIT:
                    self.hint.add(label("LEFT/RIGHT to change difficulty | SPACE to select", "Regular", (.5,.5), (60,5), 4))

                t = 0 if self.state == State.WAIT else 1.8 if self.state == State.GAME else self.t

                self.box.pos = (10,40)
                self.box.size = (100,40)

                self.rotate.angle = slide(t, 0, .85, lambda x: 1-(1-x)**2)(0, 360)

                sl = slide(t, 1.1, 1.8, lambda x: (x+x**6*3)/4)
                self.frame.pos = sl((15,45), (0,0))
                self.frame.size = sl((30,30), (120,120))

                sm = slide(t, 1.1, 1.8, lambda x: 1-(1-x)**1.5)
                self.jacket.pos = sm((15,30), (0,0))
                self.jacket.size = sm((50,50), (120,120))

                self.darken.a = sm(0, .75)

                sn = slide(t, 1.1, 1.8, lambda x: 1-(1-x)**3)
                self.orient.angle = sn(0, 90)
                self.translate.xy = sn((0,0), (67,-58))
                self.lighten.a = sn(1, .75)

            case State.ENDING | State.RESULTS:
                if self.state == State.RESULTS:
                    self.hint.add(label("SPACE to return", "Regular", (.5,.5), (60,5), 4))

                t = 1.8 - self.t

                self.box.pos = (10,10)
                self.box.size = (100,100)

                sl = slide(t, 1.1, 1.8, lambda x: (x+x**6*3)/4)
                self.frame.pos = sl((15,75), (0,0))
                self.frame.size = sl((30,30), (120,120))

                sm = slide(t, 1.1, 1.8, lambda x: 1-(1-x)**1.5)
                self.jacket.pos = sm((15,60), (0,0))
                self.jacket.size = sm((50,50), (120,120))

                self.darken.a = sm(0, .75)

                sn = slide(t, 1.1, 1.8, lambda x: 1-(1-x)**3)
                self.orient.angle = sn(0, 90)
                self.translate.xy = sn((0,30), (67,-58))
                self.lighten.a = sn(1, .75)

                first = self.results[0][0]
                last = self.results[-1][0]
                while self.i < len(self.results) * clamp(0, 1, (self.t - wait) / compute):
                    beat, judge, dt, w = self.results[self.i]
                    self.dots.add(Color(hsv=hsv_judge[judge]))
                    self.dots.add(Ellipse(pos=(55 * unlerp(first, last, beat) - 1/2,dt/Judge.BAD.value * 20 - 1/2), size=(1,1)))
                    # self.scor += weight_judge[judge]
                    self.count[judge] += 1
                    self.i += 1
                    if self.i == len(self.results):
                        for score, letter, theme in thresholds:
                            if self.scor >= score:
                                break
                        h, s, v = hsv_judge[theme]
                        self.rcolor.hsv = (h, s/2, v)
                        self.rank.clear()
                        self.rank.add(label(letter, "Bold", (.5,.5), (0,0), 20, outline_width=20, outline_color=Color(hsv=(h, s/2, v/2)).rgb))

                self.rcolor.a = slide(self.t, wait+compute, wait+compute+.1, lambda x: x**2)(0, 1)
                self.rscale.xyz = (slide(self.t, wait+compute, wait+compute+.1)(2, 1),) * 3

                self.score.clear()
                self.score.add(label(f"{self.scor}", "Bold", (1,.5), (75,0), 10))
                self.coin_count.clear()
                self.coin_count.add(label(f"{self.coins_collected}/{self.num_coins}", "Bold", (1,.5), (75,0), 10))
                for judge in Judge:
                    self.counts[judge].clear()
                    self.counts[judge].add(label(f"{int(self.count[judge])}", "Bold", (1,.5), (29,0), 6))


            case State.RETURNING:
                sl = slide(self.t, 0, .7, lambda x: 1-(1-x)**4)
                self.frame.pos = sl((15,75), (15,45))
                self.frame.size = (30,30)

                self.jacket.pos = sl((15,60), (15,30))
                self.jacket.size = (50,50)

                self.box.pos = sl((10,10), (10,40))
                self.box.size = sl((100,100), (100,40))

                self.translate.xy = sl((0,30), (0,0))

    def on_update(self, dt):
        old_t = self.t
        self.t += dt
        match self.state:
            case State.STARTING:
                if self.t >= 1.8:
                    self.cb(self.select)
                    self.cb = None
                    self.state = State.GAME
            case State.ENDING:
                if old_t < wait <= self.t:
                    self.tally = self.play_sfx(w_tally,6,True)
                elif old_t < wait+compute <= self.t:
                    self.tally.release()
                    self.play_sfx(w_whoosh, 2)
                elif wait+compute+2 <= self.t:
                    self.state = State.RESULTS
            case State.RETURNING:
                if self.t >= .7:
                    self.state = State.WAIT

        self.refresh()
