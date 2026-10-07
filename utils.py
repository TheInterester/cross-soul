from contextlib import contextmanager
import re
from fractions import Fraction
from collections.abc import Iterable, Callable
import random as rand
import math
from enum import Enum, IntEnum
from typing import TypeVar, Generic
import functools

import numpy as np

from kivy.graphics import (
    PushMatrix,
    PopMatrix,
    StencilPush,
    StencilUse,
    StencilUnUse,
    StencilPop,
    Ellipse,
    Rectangle,
    Line,
    Triangle,
    Mesh,
    Color,
    Translate,
    Scale,
    Rotate,
    MatrixInstruction,
    InstructionGroup,
    RenderContext,
    BoxShadow,
)
from kivy.graphics.texture import Texture
from kivy.core.text import Label as CoreLabel
from kivy.core.window import Window
from kivy.properties import NumericProperty, StringProperty, ListProperty, DictProperty, ColorProperty, BooleanProperty
from kivy.lang import Builder
from kivy.factory import Factory
from kivy.uix.relativelayout import RelativeLayout
from kivy.clock import Clock

from imslib.audio import Audio
from imslib.mixer import Mixer
from imslib.gfxutil import CEllipse, CRectangle

# MATH


def lerp(a, b, t):
    return a + (b - a) * t


def clamp(a, b, x):
    return min(b, max(a, x))


def unlerp(a, b, x):
    return (x - a) / (b - a)


# `slide(t, t1, t2, f)(x, y)` interpolates between x and y (supports iterables) from following curve f at time t relative to [t1,t2]
def slide(t, t1, t2, f=lambda x: x):
    k = f(clamp(0, 1, unlerp(t1, t2, t)))

    def slip(a, b):
        if isinstance(a, Iterable):
            return tuple(slip(x, y) for x, y in zip(a, b))
        return lerp(a, b, k)

    return slip


def approach(val, target, step):
        if val < target:
            return min(val + step, target)
        else:
            return max(val - step, target)


def intersect(l1, r1, l2, r2):
    return l1 <= r2 and l2 <= r1

def vadd(a, b):
    return [x + y for x, y in zip(a, b)]

def vmul(a, b):
    return [x * y for x, y in zip(a, b)]

def translate(x, y, z):
    m = np.identity(4)
    m[3, :3] = [x, y, z]
    return m

def scale(s):
    m = np.identity(4) * s
    m[3, 3] = 1
    return m


# PROGRAMMING


def invert(xs):
    return { x: i for i, x in enumerate(xs) }


T = TypeVar("T")


class Phase(IntEnum):
    """Whether a menu is transitioning in/out or not."""
    ENTER = -1
    STAY = 0
    EXIT = 1


# FORMATTING


def as_length(seconds):
    return f"{int(seconds // 60)}:{int(seconds % 60):02d}"


# DEBUG


def colored_print(code: str):
    def cprint(*args):
        print(f"\033[{code}m", end="")
        print(*args)
        print("\033[0m", end="")
    return cprint

warn = colored_print("33")
info = colored_print("92")


# EXTRA

""" Helper for rendering all children of instructiongroup. Returns True if any children render"""


def render_children(parent: InstructionGroup, children: list[InstructionGroup], scroll):
    any_render = False
    for child in children:
        vis = child.on_update(scroll)
        any_render |= vis
        render = child in parent.children
        if vis and not render:
            parent.add(child)
        if render and not vis:
            parent.remove(child)
    return any_render

def eval_bezier(pts, t):
    if len(pts) == 2:
        x1, y1 = pts[0]
        x2, y2 = pts[1]
        return lerp(x1, x2, t), lerp(y1, y2, t)
    else:
        new_pts = []
        for i in range(len(pts) - 1):
            x1, y1 = pts[i]
            x2, y2 = pts[i + 1]
            new_pts.append([lerp(x1, x2, t), lerp(y1, y2, t)])
        return eval_bezier(new_pts, t)

# KIVY

AUDIO = Audio(2)


def darken(color):
    h, s, v = color.hsv
    return Color(hsv=(h, s/2, v/2), a=color.a)


def lighten(color):
    h, s, v = color.hsv
    return Color(hsv=(h, s/2, v), a=color.a)


def instr(matrix):
    ins = MatrixInstruction()  # passing as argument doesn't work
    ins.matrix = matrix
    ins.stack = "modelview_mat"
    return ins


def label(text, variant, anchor, pos, size, quality=10, **kwargs):
    title = CoreLabel(
        text=text,
        font_size=size * quality,
        font_name=f"./assets/SourceSans3-{variant}.ttf",
        **kwargs,
    )
    title.refresh()
    w, h = title.texture.size
    height = h / quality
    width = w / quality
    return Rectangle(
        texture=title.texture,
        pos=(pos[0] - anchor[0] * width, pos[1] - anchor[1] * height),
        size=(width, height),
    )


class NoGroup:
    @staticmethod
    def add(instr):
        pass

@contextmanager
def StackFrame(group=NoGroup):
    group.add(PushMatrix())
    try:
        yield
    finally:
        group.add(PopMatrix())


def make_masker(group, mask):
    return lambda: group.add(mask)

@contextmanager
def Stencil(masker, group=NoGroup):
    group.add(StencilPush())
    masker()
    group.add(StencilUse())
    try:
        yield
    finally:
        group.add(StencilUnUse())
        masker()
        group.add(StencilPop())


def mesher(shape):
    return Mesh(
        vertices=[coord for x, y in shape for coord in (x, y, 0, 0)],
        indices=range(len(shape)),
    )


gradient = Texture.create(size=(1,256), colorfmt="rgba")
gradient.blit_buffer(bytes(j for i in range(256) for j in (255,255,255,255-i)), colorfmt="rgba")
