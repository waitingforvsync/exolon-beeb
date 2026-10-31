"""A minimal CPC 464 round Exolon's code: the reference for the BBC version (after Chase H.Q.'s tools/cpc.py).

The game runs with interrupts off and never waits for vsync, so this models only what it touches: the gate
array (inks, mode), the CRTC's registers, the PPI (vsync on port B, the AY's bus and the keyboard row on port
C) and the AY's registers (the keyboard read through register 14). It starts at &0100 with memory as the disc's
loader leaves it with no pokes: EXOLON.1 at &0100, EXOLON.2 at &6BDD, EXOLON.3 moved to &A001.

The Z80 is kosarev's (the z80 package). Plain runs count Z80 T-states. `time_passes` single-steps instead and
charges each instruction the CPC's microseconds (its memory cycles are rounded up to 1 us): ceil(T / 4), plus
the extra slot the CPC gives PUSH, RST, EX (SP), OUT/IN (C), a taken RET cc, an untaken DJNZ, LDI and LDIR's
last, (IX+d) bit operations and LD (IX+d),n.

    from cpc import CPC
    m = CPC()
    m.start_game()                       # title, then '1'
    m.run_passes(100, lambda i: {'p'})   # main-loop passes (each to &06C3), walking right
    m.screen_png('build/cpc.png')
"""
import os
import statistics
import sys

import z80
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from cpcdsk import read_dsk                             # noqa: E402

DSK = os.path.join(os.path.dirname(__file__), '..', 'docs', 'exolon.dsk')
PASS = 0x06C3                                           # the top of the main loop
PADS = (0x076D, 0x0770)                                 # the calls that pad a pass to its worst case
FRAME_T = 79872                                         # T-states a CPC frame (312 lines of 64 us at 4 MHz)
FRAME_US = 19968

# hardware colour -> guns as 0, 1 (half) or 2 (full), R G B
LEVELS = [(1, 1, 1), (1, 1, 1), (0, 2, 1), (2, 2, 1), (0, 0, 1), (2, 0, 1), (0, 1, 1), (2, 1, 1),
          (2, 0, 1), (2, 2, 1), (2, 2, 0), (2, 2, 2), (2, 0, 0), (2, 0, 2), (2, 1, 0), (2, 1, 2),
          (0, 0, 1), (0, 2, 1), (0, 2, 0), (0, 2, 2), (0, 0, 0), (0, 0, 2), (0, 1, 0), (0, 1, 2),
          (1, 0, 1), (1, 2, 1), (1, 2, 0), (1, 2, 2), (1, 0, 0), (1, 0, 2), (1, 1, 0), (1, 1, 2)]
HWRGB = [tuple((0, 128, 255)[g] for g in c) for c in LEVELS]

# CPC key numbers (row * 8 + bit). The game's own keys: O, P, Q, A, SPACE (read at &0D20).
KEYS = {'up': 0, 'right': 1, 'down': 2, 'left': 8, 'p': 27, 'o': 34, 'space': 47, 'q': 67, 'a': 69,
        '1': 64, '2': 65, 'esc': 66, 'return': 18}


def mode0_pens(b):
    """A MODE 0 byte's two pens, left then right."""
    left = (b >> 7 & 1) | (b >> 3 & 1) << 1 | (b >> 5 & 1) << 2 | (b >> 1 & 1) << 3
    right = (b >> 6 & 1) | (b >> 2 & 1) << 1 | (b >> 4 & 1) << 2 | (b & 1) << 3
    return left, right


def initial_memory(dsk=DSK):
    files = read_dsk(dsk)
    mem = bytearray(65536)
    for name, addr in (('EXOLON.1', 0x0100), ('EXOLON.2', 0x6BDD), ('EXOLON.3', 0xA001)):
        d = files[name]['data']
        mem[addr:addr + len(d)] = d
    return mem


def nops(mem, pc, t):
    """The CPC's microseconds for the instruction at pc that took t T-states."""
    n = (t + 3) // 4
    op = mem[pc]
    if op in (0xC5, 0xD5, 0xE5, 0xF5, 0xE3) or op & 0xC7 == 0xC7:
        return n + 1
    if op & 0xC7 == 0xC0 and t == 11:
        return n + 1
    if op == 0x10 and t == 8:
        return n + 1
    if op == 0xED:
        o2 = mem[(pc + 1) & 0xFFFF]
        if 0x40 <= o2 <= 0x7F and o2 & 6 == 0:
            return n + 1
        if o2 in (0xA0, 0xA1, 0xA2, 0xA3, 0xA8, 0xA9, 0xAA, 0xAB):
            return n + 1
        if o2 in (0xB0, 0xB1, 0xB2, 0xB3, 0xB8, 0xB9, 0xBA, 0xBB) and t == 16:
            return n + 1
    if op in (0xDD, 0xFD) and mem[(pc + 1) & 0xFFFF] in (0xE5, 0xE3, 0x36, 0xCB):
        return n + 1
    return n


class CPC:
    def __init__(self, dsk=DSK, stretch=1.156):
        self.frame_t = int(FRAME_T / stretch)               # (for the vsync bit only: nothing polls it)
        self.pen = 0
        self.inks = [20] * 17
        self.mode = 1
        self.crtc = [0] * 32
        self.crtcsel = 0
        self.ppi = [0xFF, 0, 0, 0]
        self.psgsel = 0
        self.psg = [0] * 16
        self.psglog = []                                    # (T, register, value)
        self.keys = set()
        self.z = z80.Z80Machine()
        self.z.set_memory_block(0, initial_memory(dsk))
        self.mem = self.z.memory
        self.z.pc = 0x0100
        self.z.sp = 0x0100
        self.z.set_input_callback(self.read_port)
        self.z.set_output_callback(self.write_port)
        self.t = 0
        self.budget = 0

    # the hardware

    def now(self):
        return self.t + self.budget - self.z.ticks_to_stop

    def write_port(self, port, value):
        if port & 0xC000 == 0x4000:                         # gate array
            f = value >> 6
            if f == 0:
                self.pen = 16 if value & 0x10 else value & 15
            elif f == 1:
                self.inks[self.pen] = value & 31
            elif f == 2:
                self.mode = value & 3
        if port & 0x4000 == 0:                              # CRTC
            f = port >> 8 & 3
            if f == 0:
                self.crtcsel = value & 31
            elif f == 1:
                self.crtc[self.crtcsel] = value
        if port & 0x0800 == 0:                              # PPI
            f = port >> 8 & 3
            if f == 3:
                if value & 0x80:
                    self.ppi[3] = value
                else:
                    bit = 1 << (value >> 1 & 7)
                    self.ppi[2] = self.ppi[2] | bit if value & 1 else self.ppi[2] & ~bit
                    self.psg_bus()
            else:
                self.ppi[f] = value
                if f == 2:
                    self.psg_bus()

    def psg_bus(self):
        f = self.ppi[2] >> 6
        if f == 3:
            self.psgsel = self.ppi[0] & 15
        elif f == 2:
            self.psg[self.psgsel] = self.ppi[0]
            self.psglog.append((self.now(), self.psgsel, self.ppi[0]))

    def read_port(self, port):
        if port & 0x0800 == 0:
            f = port >> 8 & 3
            if f == 0:
                if self.ppi[2] >> 6 == 1:
                    if self.psgsel == 14:
                        row = self.ppi[2] & 15
                        return 0xFF & ~sum(1 << (k & 7) for k in self.keys if k >> 3 == row)
                    return self.psg[self.psgsel]
                return 0xFF
            if f == 1:
                return 0x5E | (self.now() % self.frame_t < 8 * 256)
            if f == 2:
                return self.ppi[2]
        return 0xFF

    # running

    def hold(self, keys):
        self.keys = {KEYS.get(k, k) for k in keys}

    def run_to(self, addr, max_t=50 * FRAME_T):
        """Run until PC is addr (one instruction at least); addr None runs max_t. False if max_t passes first."""
        z = self.z
        if addr is not None:
            z.set_breakpoint(addr)
            if z.pc == addr:
                z.step_over_breakpoint()
        hit = False
        left = max_t
        while left > 0 and not hit:
            self.budget = min(left, 1 << 22)
            z.ticks_to_stop = self.budget
            events = z.run()
            ran = self.budget - z.ticks_to_stop
            self.t += ran
            left -= ran
            self.budget = 0
            hit = addr is not None and bool(events & z._BREAKPOINT_HIT) and z.pc == addr
        if addr is not None:
            z.clear_breakpoint(addr)
        return hit

    def start_game(self):
        """The title for 100 frames, then '1', then on to the first pass."""
        self.run_to(None, 100 * FRAME_T)
        self.hold({'1'})
        self.run_to(None, 10 * FRAME_T)
        self.hold(set())
        if not self.run_to(PASS, 400 * FRAME_T):
            raise RuntimeError(f'no pass: PC &{self.z.pc:04X}')

    def run_passes(self, n, keys_for=None):
        """Run n passes of the main loop, each to &06C3; keys_for(i) gives the keys held in pass i."""
        for i in range(n):
            if keys_for:
                self.hold(keys_for(i))
            if not self.run_to(PASS, 40 * FRAME_T):
                raise RuntimeError(f'no pass within 40 frames: PC &{self.z.pc:04X}')

    def time_passes(self, n, keys_for=None):
        """Single-step n passes with the CPC's timing: [(us, of which padding)] a pass. Starts at a pass."""
        z, mem = self.z, self.mem
        assert z.pc == PASS
        out = []
        prev = z.frame_tick
        for i in range(n):
            if keys_for:
                self.hold(keys_for(i))
            us = pad = 0
            back = None
            while True:
                pc = z.pc
                z.ticks_to_stop = 1
                z.run()
                f = z.frame_tick
                t = (f - prev) % 100000                     # (frame_tick wraps at 100,000)
                prev = f
                self.t += t
                c = nops(mem, pc, t)
                us += c
                if pc in PADS:
                    back = pc + 3
                if back is not None:
                    pad += c
                    if z.pc == back:
                        back = None
                if z.pc == PASS:
                    break
            out.append((us, pad))
        return out

    # looking

    def screen_image(self, scale=2):
        """The screen with MODE 0's pixels twice as wide as tall, each line doubled."""
        ma = self.crtc[12] << 8 | self.crtc[13]
        base, offset = (ma >> 12 & 3) * 0x4000, (ma & 0x3FF) * 2
        width = self.crtc[1] * 2
        rows = self.crtc[6] or 25
        img = Image.new('RGB', (width * 4, rows * 8))
        px = img.load()
        rgb = [HWRGB[self.inks[p]] for p in range(16)]
        for y in range(rows * 8):
            a = base + (y & 7) * 0x800
            for x in range(width):
                left, right = mode0_pens(self.mem[a + ((offset + (y >> 3) * width + x) & 0x7FF)])
                px[x * 4, y] = px[x * 4 + 1, y] = rgb[left]
                px[x * 4 + 2, y] = px[x * 4 + 3, y] = rgb[right]
        return img.resize((img.width * scale // 2, img.height * scale), Image.NEAREST)

    def screen_png(self, path):
        self.screen_image().save(path)


if __name__ == '__main__':
    import random
    m = CPC()
    m.start_game()
    rnd = random.Random(1)
    held = [set()]

    def keys(i):
        if i % 25 == 0:
            held[0] = set(rnd.sample(['p', 'o', 'q', 'a', 'space', 'space', 'space'], 2))
        return held[0]

    n = int(sys.argv[1]) if len(sys.argv) > 1 else 300
    times = m.time_passes(n, keys)[10:]
    loop = [u for u, _ in times]
    work = [u - p for u, p in times]
    q = lambda v, f: sorted(v)[int(f * (len(v) - 1))]   # noqa: E731
    print(f'{len(loop)} passes: median {statistics.median(loop):,.0f} us ({statistics.median(loop) / FRAME_US:.2f} frames), '
          f'max {max(loop):,} us; {1e6 / statistics.median(loop):.1f} passes a second')
    print(f'work without the padding: median {statistics.median(work):,.0f} us, 90% {q(work, .9):,} us, max {max(work):,} us')
    os.makedirs('build', exist_ok=True)
    m.screen_png('build/cpc.png')
