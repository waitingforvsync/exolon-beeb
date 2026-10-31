"""A minimal 48K Spectrum round the original Exolon (Hewson, 1987): the reference the CPC version came from.

The tape (docs/Exolon.tzx) is loaded once by SkoolKit's simulated LOAD, through the Hewson loader, to the game's
entry at &6D60 (the loader moves &658F-&F82F up to &6D60-&FFFF, sets SP = &6D5E, EI, JP &6D60):

    .venv/bin/tap2sna.py --start 0x6D60 -c finish-tape=1 -c timeout=500 docs/Exolon.tzx build/spec/exolon.z80

This models what the game touches: the 48K ROM (SkoolKit's), an interrupt every 69,888 T (IM 1 or IM 2), the
keyboard's half-rows on port &FE (bits 0-4 low for keys down) and the border. Kempston (port &1F) reads 0. No
contention: T-states are plain.

    from spectrum import Spectrum
    m = Spectrum()
    m.run_frames(300)                        # 50 a second
    m.hold({'1'}); m.run_frames(5); m.hold(set())
    m.screen_png('build/spec.png')
"""
import os
import sys

import z80
from PIL import Image
from skoolkit.snapshot import Snapshot

ROOT = os.path.join(os.path.dirname(__file__), '..')
SNAPSHOT = os.path.join(ROOT, 'build', 'spec', 'exolon.z80')
ROM = os.path.join(os.path.dirname(__import__('skoolkit').__file__), 'resources', '48.rom')
FRAME_T = 69888                                     # T-states a 48K frame (224 x 312)

# key name -> (half-row, bit): rows by the port's high byte bit 0-7
_ROWS = ['shift z x c v', 'a s d f g', 'q w e r t', '1 2 3 4 5', '0 9 8 7 6', 'p o i u y', 'enter l k j h',
         'space sym m n b']
KEYS = {name: (row, bit) for row, names in enumerate(_ROWS) for bit, name in enumerate(names.split())}

# the Spectrum's colours: 0 black, 1 blue, 2 red, 3 magenta, 4 green, 5 cyan, 6 yellow, 7 white; bright or not
RGB = [tuple(((c >> 1 & 1) * v, (c >> 2 & 1) * v, (c & 1) * v)) for v in (205, 255) for c in range(8)]


class Spectrum:
    def __init__(self, snapshot=SNAPSHOT):
        snap = Snapshot.get(snapshot)
        mem = bytearray(open(ROM, 'rb').read()) + bytearray(snap.ram(-1))
        assert len(mem) == 65536
        self.z = z80.Z80Machine()
        self.z.set_memory_block(0, mem)
        self.mem = self.z.memory
        z = self.z
        z.pc, z.sp = snap.pc, snap.sp
        z.af = snap.a << 8 | snap.f
        z.bc, z.de, z.hl, z.ix, z.iy = snap.bc, snap.de, snap.hl, snap.ix, snap.iy
        z.i, z.r = snap.i, snap.r
        z.int_mode = snap.im
        z.iff1 = z.iff2 = 1                         # (the loader's EI, just before JP &6D60)
        self.romcopy = bytes(mem[:0x4000])
        z.set_input_callback(self.read_port)
        z.set_output_callback(self.write_port)
        self.keys = set()
        self.border = snap.border
        self.frames = 0
        self.t = 0                                  # T-states run
        self.into = 0                               # T-states into the current frame

    # the hardware

    def read_port(self, port):
        if port & 1 == 0:                           # the ULA
            rows = ~port >> 8 & 0xFF
            v = 0x1F
            for name in self.keys:
                row, bit = KEYS[name]
                if rows >> row & 1:
                    v &= ~(1 << bit)
            return v | 0xA0
        return 0x00 if port & 0xFF == 0x1F else 0xFF

    def write_port(self, port, value):
        if port & 1 == 0:
            self.border = value & 7

    # running

    def hold(self, keys):
        self.keys = set(keys)

    def run_t(self, t):
        """Run t T-states, taking the frame's interrupt at each frame boundary."""
        z = self.z
        while t > 0:
            step = min(t, FRAME_T - self.into)
            z.ticks_to_stop = step
            z.run()
            ran = step - z.ticks_to_stop
            self.t += ran
            self.into += ran
            t -= ran
            if self.into >= FRAME_T:
                self.into -= FRAME_T
                self.frames += 1
                z.on_handle_active_int()
            if self.mem[:0x4000] != self.romcopy:   # (writes to the ROM are discarded on a real 48K)
                self.mem[:0x4000] = self.romcopy

    def run_frames(self, n):
        self.run_t(n * FRAME_T - self.into)

    def run_to(self, addr, max_t=50 * FRAME_T):
        """Run until PC is addr (one instruction at least). False if max_t T-states pass first."""
        z = self.z
        z.set_breakpoint(addr)
        if z.pc == addr:
            z.step_over_breakpoint()
        left = max_t
        hit = False
        while left > 0 and not hit:
            step = min(left, FRAME_T - self.into)
            z.ticks_to_stop = step
            events = z.run()
            ran = step - z.ticks_to_stop
            self.t += ran
            self.into += ran
            left -= ran
            hit = bool(events & z._BREAKPOINT_HIT) and z.pc == addr
            if self.into >= FRAME_T:
                self.into -= FRAME_T
                self.frames += 1
                if not hit:
                    z.on_handle_active_int()
        z.clear_breakpoint(addr)
        return hit

    # looking

    def screen_image(self, scale=2):
        img = Image.new('RGB', (256, 192))
        px = img.load()
        m = self.mem
        for y in range(192):
            base = 0x4000 | (y & 0xC0) << 5 | (y & 7) << 8 | (y & 0x38) << 2
            for cx in range(32):
                attr = m[0x5800 + (y >> 3) * 32 + cx]
                bright = 8 if attr & 0x40 else 0
                ink, paper = RGB[(attr & 7) + bright], RGB[(attr >> 3 & 7) + bright]
                b = m[base + cx]
                for i in range(8):
                    px[cx * 8 + i, y] = ink if b & (0x80 >> i) else paper
        return img.resize((256 * scale, 192 * scale), Image.NEAREST)

    def screen_png(self, path):
        self.screen_image().save(path)


if __name__ == '__main__':
    m = Spectrum()
    m.run_frames(int(sys.argv[1]) if len(sys.argv) > 1 else 200)
    print('PC &%04X, frames %d, IM %d, I &%02X' % (m.z.pc, m.frames, m.z.int_mode, m.z.i))
    m.screen_png(sys.argv[2] if len(sys.argv) > 2 else 'build/spec.png')
