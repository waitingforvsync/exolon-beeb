"""The original's plots as commands for the BBC's plotter benchmark (src/bench.6502, tools/bench.mjs).

    .venv/bin/python tools/benchlog.py --zone 0 --passes 400 --keys random:1 build/bench/zone0.bin

Runs the CPC original (tools/plotlog.py) and turns each pass's plots into bench.6502's commands: a large sprite
(the 32- and 16-line sets, known by its save area) that moves or changes gets its edges in phase 1 and its draw
in phase 2, or goes; an 8-line sprite is XORed off in phase 1, on in phase 2. In a pass: the 8-line sprites off,
the large sprites' edges (or their going), their draws, the 8-line sprites on, so no store meets an 8-line
sprite on the screen (and each phase's in the original's order). The padding, the dots (the laser and the guns'
shots) and the tiles' animations are left out. The file is each pass's commands, after a 2-byte length; a pass
with the screen cleared (a zone change) ends it.
"""
import argparse
import os
import struct
import sys
from collections import Counter

sys.path.insert(0, os.path.dirname(__file__))
import plotlog                                      # noqa: E402


def sprite(p):
    base = {'player': 0, 'obj16': 50, 'obj8': 140}[p.kind]
    return base + 2 * p.frame + (p.x & 1)


def commands(log):
    """The passes' commands, and the counts of the original's quirks smoothed: a large sprite plotted twice in a
    pass (its last plot kept: the BBC plots a sprite once a pass), and an 8-line image XORed off that isn't on
    the screen (a new object's first erase: it cancels the pass's XOR on of the same image, or else is an XOR
    on). The 8-line set's blank frame (6) is left out: it XORs nothing."""
    slots, out, shown = {}, [], Counter()
    twice = unshown = 0
    for plots in log:
        if any(p.kind == 'clear' for p in plots):
            break
        large, offs, ons = {}, [], []               # large: slot -> (phase 1's command, phase 2's or None)
        for p in plots:
            if p.pad:
                continue
            if p.kind in ('player', 'obj16'):
                slot = slots.setdefault(p.save, len(slots))
                assert slot < 16, 'more large sprites than slots'
                twice += slot in large
                cmd = (slot, sprite(p), p.x, p.y)
                large[slot] = ((1,) + cmd, (2,) + cmd) if p.draw else ((3, slot), None)
            elif p.kind == 'obj8' and p.frame != 6:   # (frame 6 is blank: nothing to XOR)
                (offs if p.erase else ons).append((sprite(p), p.x, p.y))
        kept = []
        for o in offs:
            if shown[o]:
                shown[o] -= 1
                kept.append(o)
            else:
                unshown += 1
                if o in ons:
                    ons.remove(o)
                else:
                    ons.append(o)
        for o in ons:
            shown[o] += 1
        cmds = [(4,) + o for o in kept] + [a for a, _ in large.values()] + [b for _, b in large.values() if b] + \
            [(4,) + o for o in ons]
        c = bytes(b for cmd in cmds for b in cmd) + b'\0'
        assert len(c) <= 1024, 'a pass longer than CmdBuf'
        out.append(c)
    return out, twice, unshown


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--zone', type=int, default=0)
    ap.add_argument('--passes', type=int, default=400)
    ap.add_argument('--keys', default='random:1')
    a = ap.parse_args()
    keys = plotlog.random_keys(int(a.keys.split(':')[1])) if a.keys.startswith('random:') else (lambda i: set(a.keys.split()))
    passes, twice, unshown = commands(plotlog.run(zone=a.zone, passes=a.passes, keys=keys))
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    with open(a.out, 'wb') as f:
        for c in passes:
            f.write(struct.pack('<H', len(c)) + c)
    print(f'{len(passes)} passes, {sum(len(c) for c in passes)} bytes of commands, the longest {max(map(len, passes))}; '
          f'{twice} large plots dropped for a later one in their pass, {unshown} XORs off of 8-line images not shown')


if __name__ == '__main__':
    main()
