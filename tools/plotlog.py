"""Every plot the CPC original makes, pass by pass (docs/cpc-graphics.md): the workload for the BBC's plotters.

Runs the harness (tools/cpc.py) for n passes with given keys and logs each call of a screen-writing routine:
which routine, which graphic and frame, where, and whether it was padding (&2B88, &2B9C).

    .venv/bin/python tools/plotlog.py --zone 0 --passes 400 --keys random:1          # summary
    .venv/bin/python tools/plotlog.py --zone 5 --passes 300 --keys p --log out.txt   # every plot, as text

    import plotlog
    log = plotlog.run(zone=0, passes=400, keys=plotlog.random_keys(1))
    log[i]                  # pass i: a list of Plot

Each Plot: kind ('player', 'obj16', 'obj8', 'shot', 'spark', 'block', 'clear'), the routine's address, the
caller (return address), frame (or block), set (blocks), x and y of the new image (MODE 0 pixels 0-127, lines
0-191; blocks also give row and column), and for the player and 16-line objects (which XOR the old image off
and the new on in one call) ox, oy of the old image, with 'erase' and 'draw' telling whether each half did
anything (a save area of zeros erases nothing; a blank frame draws nothing). An 8-line object is one XOR a
call: its call site says whether it erases or draws (ERASE8, DRAW8; elsewhere, an image XORed where the same
image already is counts as an erase), and PAIRS8 pairs an erase with the draw that moves the object. pad marks
the padding's dummy plots. nbytes is the screen bytes the call writes (XOR read-modify-writes count once).
Passes with a screen clear (a zone change) are left out of the summary's per-pass counts.

Keys: 'random:SEED' (two of P, P, O, Q, A, SPACE, SPACE, SPACE, changed every 25 passes: cpc.py's own run with
right weighted twice), or keys held throughout ('p', 'pq', 'o space', ...). 'player' is the 32-line plotter
(&07D9), which also draws the popups (frame 24).
"""
import argparse
import collections
import os
import random
import statistics
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cpc import CPC, FRAME_T, PASS                      # noqa: E402

PLAYER, OBJ16, OBJ8 = 0x07D9, 0x0B5F, 0x2020
SHOT, SPARK = 0x10F5, 0x1D9A                            # the player's shot (1 line); the guns' shots (2 lines)
BLOCKS = {0x3B92: 0, 0x3BDB: 1, 0x3C0E: 2, 0x3C43: 3, 0x3C94: 4}   # the block plotters, modes 0-4
CLEARS = {0x3E0C: 'playfield', 0x3DFD: 'screen'}
PADS = {0x2B98: 'pad8', 0x2BAE: 'pad16'}                # the padding's return addresses
ENTRIES = (PLAYER, OBJ16, OBJ8, SHOT, SPARK) + tuple(BLOCKS) + tuple(CLEARS)
ZERO16 = 0x3F1E                                         # a save area of zeros: nothing erased, nothing saved
# 8-line objects (one XOR a call): which call sites erase and which draw (return addresses), and the pairs
# that move one object (erase the old, draw the new)
ERASE8 = {0x1FA5: 'grenade', 0x2557: 'blinker', 0x2747: 'frame 7 mover', 0x287A: 'frame 7 removed',
          0x2AF4: 'frame 8 mover', 0x2B57: 'frame 8 removed', 0x228E: 'debris'}
DRAW8 = {0x1F77: 'grenade thrown', 0x1FE4: 'grenade', 0x255C: 'blinker', 0x2794: 'frame 7 mover',
         0x2838: 'frame 4 at set-up', 0x2AC3: 'frame 8 spawned', 0x2B06: 'frame 8 mover', 0x2251: 'debris spawned',
         0x22A9: 'debris'}
PAIRS8 = {0x1FA5: 0x1FE4, 0x2557: 0x255C, 0x2747: 0x2794, 0x2AF4: 0x2B06, 0x228E: 0x22A9}
TELEPORT = (8, 16)                                      # a move wider or taller than this is a respawn


class Plot:
    __slots__ = ('kind', 'routine', 'caller', 'frame', 'set', 'x', 'y', 'ox', 'oy', 'save', 'erase', 'draw',
                 'pad', 'nbytes', 'row', 'col', 'mode')

    def __init__(self, **k):
        for s in self.__slots__:
            setattr(self, s, k.get(s))

    def __repr__(self):
        s = f'{self.kind:6} &{self.routine:04X} from &{self.caller:04X}'
        if self.kind == 'block':
            s += f' mode {self.mode} set &{self.set:04X} block {self.frame:3} row {self.row} col {self.col}'
        elif self.kind == 'clear':
            s += f' {self.frame}'
        else:
            s += f' frame {self.frame} at ({self.x}, {self.y})'
        if self.ox is not None:
            s += f' from ({self.ox}, {self.oy}) save &{self.save:04X}'
        if self.erase is not None:
            s += f' {"erase" if self.erase else "-"}/{"draw" if self.draw else "-"}'
        if self.pad:
            s += f' PAD({self.pad})'
        return s + f' {self.nbytes}b'


def random_keys(seed):
    rnd = random.Random(seed)
    held = [set()]

    def keys(i):
        if i % 25 == 0:
            held[0] = set(rnd.sample(['p', 'p', 'o', 'q', 'a', 'space', 'space', 'space'], 2))
        return held[0]
    return keys


def fixed_keys(s):
    ks = set(s.split()) if ' ' in s else set(s)
    return lambda i: ks


def start(zone=None, invulnerable=False):
    """The harness at the first pass of a game, in zone (the disc's poke) or zone 0."""
    m = CPC()
    if zone is not None:
        m.mem[0x010E:0x0111] = b'\0\0\0'
        m.mem[0x12FA] = zone
    if invulnerable:                                    # the disc's poke: the timer &078C kept at 1
        m.mem[0x0779] = 0                               # (NOP its DEC A) and not reset at a zone
        m.mem[0x1278:0x127B] = b'\0\0\0'
        m.mem[0x078C] = 1
    m.start_game()
    return m


def blank(mem, a, n):
    return not any(mem[a:a + n])


def run(zone=None, passes=300, keys=None, invulnerable=False, m=None):
    """[[Plot] a pass] for passes main-loop passes."""
    m = m or start(zone, invulnerable)
    z, mem = m.z, m.mem
    log = []
    on8 = collections.Counter()                         # 8-line images XORed on elsewhere: (frame, x, y)
    for i in range(passes):
        if keys:
            m.hold(keys(i))
        plots = []
        for a in ENTRIES + (PASS,):
            z.set_breakpoint(a)
        z.step_over_breakpoint() if z.pc in ENTRIES + (PASS,) else None
        left = 400 * FRAME_T
        while True:
            m.budget = min(left, 1 << 22)
            z.ticks_to_stop = m.budget
            ev = z.run()
            ran = m.budget - z.ticks_to_stop
            m.t += ran
            left -= ran
            m.budget = 0
            pc = z.pc
            if pc == PASS and ev & z._BREAKPOINT_HIT:
                break
            if left <= 0:
                raise RuntimeError(f'pass {i}: no pass within 400 frames, PC &{pc:04X}')
            if not ev & z._BREAKPOINT_HIT:
                continue
            ret = mem[z.sp] | mem[z.sp + 1] << 8
            p = Plot(routine=pc, caller=ret, pad=PADS.get(ret))
            if pc in (PLAYER, OBJ16):
                w, h = (6, 32) if pc == PLAYER else (4, 16)
                base = 0x93CD + 192 * z.a if pc == PLAYER else 0xA68D + 64 * z.a
                p.kind = 'player' if pc == PLAYER else 'obj16'
                p.frame, p.y, p.x, p.oy, p.ox, p.save = z.a, z.d, z.e, z.b, z.c, z.hl
                p.erase = not blank(mem, z.hl, (w + 1) * h)
                p.draw = not blank(mem, base, w * h)
                p.nbytes = 2 * (w + 1) * h
            elif pc == OBJ8:
                p.kind, p.frame, p.y, p.x, p.nbytes = 'obj8', z.a, z.d, z.e, 24
                if ret in ERASE8 or ret in DRAW8:
                    p.erase, p.draw = ret in ERASE8, ret in DRAW8
                else:                                   # elsewhere (and the padding): by what's on screen
                    key = (z.a, z.e, z.d)
                    p.erase = on8[key] > 0
                    p.draw = not p.erase
                    on8[key] += -1 if p.erase else 1
            elif pc in (SHOT, SPARK):
                p.kind = 'shot' if pc == SHOT else 'spark'
                p.y, p.x = z.d, z.e
                p.nbytes = (3 if z.e & 1 else 2) if pc == SHOT else 2
            elif pc in BLOCKS:
                p.kind, p.mode, p.frame, p.row, p.col = 'block', BLOCKS[pc], z.a, z.d, z.e
                p.set = mem[0x3BA1] | mem[0x3BA2] << 8
                p.x, p.y = z.e * 4, z.d * 8
                skip = BLOCKS[pc] in (0, 3) and z.e & 0x20
                p.nbytes = 0 if skip else 16
            elif pc in CLEARS:
                p.kind, p.frame = 'clear', CLEARS[pc]
                p.nbytes = 11264 if pc == 0x3E0C else 16384
            plots.append(p)
            z.step_over_breakpoint()
        for a in ENTRIES + (PASS,):
            z.clear_breakpoint(a)
        log.append(plots)
    return log


def q(v, f):
    v = sorted(v)
    return v[int(f * (len(v) - 1))] if v else 0


def summary(log, out=print):
    """Plots and bytes a pass (padding left out), and each kind's largest move in one plot."""
    n = len(log)
    zc = [i for i, ps in enumerate(log) if any(p.kind == 'clear' for p in ps)]
    if zc:
        out(f'{n} passes, {len(zc)} of them a zone change (passes {", ".join(map(str, zc))}): left out of '
            'the per-pass counts')
    play = [ps for i, ps in enumerate(log) if i not in zc]
    plots = [sum(1 for p in ps if not p.pad) for ps in play]
    nbytes = [sum(p.nbytes for p in ps if not p.pad) for ps in play]
    pads = [sum(1 for p in ps if p.pad) for ps in play]
    out(f'{len(play)} passes of play')
    out(f'  plots a pass (padding left out): median {statistics.median(plots):.0f}, 90% {q(plots, .9)}, '
        f'max {max(plots)}; padding plots: median {statistics.median(pads):.0f}, max {max(pads)}')
    out(f'  bytes a pass (padding left out): median {statistics.median(nbytes):,.0f}, 90% {q(nbytes, .9):,}, '
        f'max {max(nbytes):,}')
    kinds = collections.defaultdict(list)
    for ps in play:
        c = collections.Counter(p.kind for p in ps if not p.pad)
        for k in ('player', 'obj16', 'obj8', 'shot', 'spark', 'block', 'clear'):
            kinds[k].append(c[k])
    for k, v in kinds.items():
        if any(v):
            out(f'  {k:6}: a pass median {statistics.median(v):.0f}, 90% {q(v, .9)}, max {max(v)}')
    # moves: the player and 16-line objects, new against old in one call (both halves live); 8-line objects,
    # an erase and the next draw of its pair (PAIRS8)
    moves = collections.defaultdict(lambda: {'dx': 0, 'dy': 0, 'n': 0, 'frames': set(), 'jumps': []})

    def note(key, p, ox, oy):
        mv = moves[key]
        dx, dy = abs(p.x - ox), abs(p.y - oy)
        if dx > TELEPORT[0] or dy > TELEPORT[1]:
            mv['jumps'].append((ox, oy, p.x, p.y))
            return
        mv['dx'], mv['dy'] = max(mv['dx'], dx), max(mv['dy'], dy)
        mv['n'] += 1
        mv['frames'].add(p.frame)

    for ps in log:
        pend = {}
        for p in ps:
            if p.pad:
                continue
            if p.kind in ('player', 'obj16') and p.erase and p.draw:
                note((p.kind, p.caller), p, p.ox, p.oy)
            elif p.kind == 'obj8':
                if p.caller in PAIRS8:
                    pend[PAIRS8[p.caller]] = p
                elif p.caller in pend:
                    e = pend.pop(p.caller)
                    note(('obj8', e.caller), p, e.x, e.y)
    out(f'  largest move in one plot (x in pixels, y in lines), by kind and caller; moves over '
        f'{TELEPORT[0]} x or {TELEPORT[1]} y counted apart as jumps (respawns):')
    for (k, c), mv in sorted(moves.items()):
        frames = ','.join(str(f) for f in sorted(mv['frames']))
        name = f' ({ERASE8[c]})' if k == 'obj8' and c in ERASE8 else ''
        out(f'    {k:6} from &{c:04X}{name}: dx {mv["dx"]:2}, dy {mv["dy"]:2} over {mv["n"]:5} moves; '
            f'frames {frames}' + (f'; {len(mv["jumps"])} jumps' if mv['jumps'] else ''))
    # what else touches the grid in play
    blk = collections.Counter((p.mode, p.caller, p.set) for ps in log for p in ps if p.kind == 'block')
    if blk:
        out('  blocks plotted (mode, caller, set: count):')
        for (mode, c, s), cnt in sorted(blk.items()):
            out(f'    mode {mode} from &{c:04X} set &{s:04X}: {cnt} ({cnt / n:.2f} a pass)')


if __name__ == '__main__':
    ap = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    ap.add_argument('--zone', type=int)
    ap.add_argument('--passes', type=int, default=300)
    ap.add_argument('--keys', default='random:1')
    ap.add_argument('--invulnerable', action='store_true')
    ap.add_argument('--log', help='write every plot to this file')
    a = ap.parse_args()
    kf = random_keys(int(a.keys[7:])) if a.keys.startswith('random:') else fixed_keys(a.keys)
    lg = run(a.zone, a.passes, kf, a.invulnerable)
    if a.log:
        with open(a.log, 'w') as f:
            for i, ps in enumerate(lg):
                f.write(f'pass {i}: {len(ps)} plots\n')
                for p in ps:
                    f.write(f'  {p!r}\n')
    summary(lg)
