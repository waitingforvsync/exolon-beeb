"""The original's plots as commands for the BBC's plotter benchmark (src/bench.6502, tools/bench.mjs).

    .venv/bin/python tools/benchlog.py --zone 0 --passes 400 --keys random:1 build/bench/zone0.bin

Runs the CPC original (tools/plotlog.py) and turns each pass's plots into bench.6502's commands: a large sprite
(the 32- and 16-line sets, known by its save area) that moves or changes gets its edges in phase 1 and its draw
in phase 2, or goes; an 8-line sprite is XORed off in phase 1, on in phase 2. The padding, the dots (the laser
and the guns' shots) and the tiles' animations are left out. The file is each pass's commands, after a 2-byte
length; a pass with the screen cleared (a zone change) ends it.
"""
import argparse
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import plotlog                                      # noqa: E402


def sprite(p):
    base = {'player': 0, 'obj16': 50, 'obj8': 140}[p.kind]
    return base + 2 * p.frame + (p.x & 1)


def commands(log):
    slots, out = {}, []
    for plots in log:
        if any(p.kind == 'clear' for p in plots):
            break
        one, two = bytearray(), bytearray()
        for p in plots:
            if p.pad:
                continue
            if p.kind in ('player', 'obj16'):
                slot = slots.setdefault(p.save, len(slots))
                assert slot < 16, 'more large sprites than slots'
                if p.draw:
                    one += bytes((1, slot, sprite(p), p.x, p.y))
                    two += bytes((2, slot, sprite(p), p.x, p.y))
                else:
                    one += bytes((3, slot))
            elif p.kind == 'obj8':
                (one if p.erase else two).extend((4, sprite(p), p.x, p.y))
        cmds = bytes(one + two + b'\0')
        assert len(cmds) <= 1024, 'a pass longer than CmdBuf'
        out.append(cmds)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--zone', type=int, default=0)
    ap.add_argument('--passes', type=int, default=400)
    ap.add_argument('--keys', default='random:1')
    a = ap.parse_args()
    keys = plotlog.random_keys(int(a.keys.split(':')[1])) if a.keys.startswith('random:') else (lambda i: set(a.keys.split()))
    passes = commands(plotlog.run(zone=a.zone, passes=a.passes, keys=keys))
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    with open(a.out, 'wb') as f:
        for c in passes:
            f.write(struct.pack('<H', len(c)) + c)
    print(f'{len(passes)} passes, {sum(len(c) for c in passes)} bytes of commands, the longest {max(map(len, passes))}')


if __name__ == '__main__':
    main()
