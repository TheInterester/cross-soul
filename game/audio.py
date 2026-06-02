from utils import *

import numpy as np
from imslib.wavegen import WaveGenerator


# prevents error if self.frame is set too low or too high
class WaveGen(WaveGenerator):
    def __init__(self, wave_source):
        super().__init__(wave_source)

    def generate(self, num_frames, num_channels):
        if self.paused:
            return super().generate(num_frames, num_channels)

        if self.frame + num_frames <= 0:
            self.frame += num_frames
            return np.zeros(num_frames * num_channels), True
        elif self.frame < 0:
            frame = self.frame
            self.frame = 0
            output, continue_flag = super().generate(frame + num_frames, num_channels)
            self.frame = frame + num_frames
            return np.append(np.zeros(-frame * num_channels), output), True
        elif self.frame < self.source.wave.getnframes():
            frame = self.frame
            output, continue_flag = super().generate(num_frames, num_channels)
            self.frame = frame + num_frames
            return output, True
        else:
            self.frame += num_frames
            return np.zeros(num_frames * num_channels), True


# Handles something about Audio.
#   functions as the clock (returns song time elapsed)
class AudioController(object):
    def __init__(self, mixer, file, bpm, off):
        self.mixer = mixer
        self.gen = WaveGen(file)
        self.gen.pause()
        self.mixer.add(self.gen)

        self.bps = bpm / 60
        self.off = off
        """time (seconds) to treat beginning of audio file as"""
        self.end = (file.wave.getnframes() / Audio.sample_rate + self.off) * self.bps

    def play(self):
        self.gen.play()

    def pause(self):
        self.gen.pause()

    def scrub(self, beats):
        self.gen.frame = int(self.gen.frame + beats / self.bps * Audio.sample_rate)

    # start / stop the song
    def toggle(self):
        if self.gen.paused:
            self.play()
        else:
            self.pause()

    # return current time (in seconds) of song
    def get_time(self):
        return self.gen.frame / Audio.sample_rate

    def get_beat(self):
        return (self.get_time() + self.off) * self.bps

    def set_time(self, time):
        self.gen.frame = int(time * Audio.sample_rate)

    def set_beat(self, beat):
        self.set_time(beat / self.bps - self.off)

    def beat_to_time(self, beat):
        return beat / self.bps - self.off

    def reset(self):
        self.gen.reset()

    def kill(self):
        self.mixer.remove(self.gen)

    def done(self):
        return self.gen.frame == self.gen.source.wave.getnframes()
