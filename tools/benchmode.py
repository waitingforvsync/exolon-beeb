"""A plot log's commands (tools/benchlog.py) recast for another way of drawing the large sprites, to time against
the self-erasing one (D7) in src/bench.6502:

    .venv/bin/python tools/benchmode.py xor build/bench/zone94.bin build/bench/zone94x.bin
    .venv/bin/python tools/benchmode.py hybrid build/bench/zone94.bin build/bench/zone94h.bin

- xor: every large sprite XORed off its old place and on at its new (5), or off (6) when it goes, as the CPC and
  the Spectrum do; no dirty edges.
- hybrid: a large sprite self-erases as before (1, 2, 3) unless its box (its old rectangle and its new, both
  drawn as the BBC clips them) meets another large sprite's box (a sprite not plotted this pass: its rectangle);
  then it's XORed (5, 6). A sprite only ever stored straight where no other one is, so the two ways mix
  exactly: every pass's screen is the same as xor's.
- hybrid8: as hybrid, a large sprite's box meeting an 8-line sprite's (where it's XORed off or on this pass)
  making it XORed too: so no store ever meets an 8-line sprite, whatever the order of the plots.
The 8-line sprites' XORs are left where they are. A pass's order (benchlog.py's) is kept, a 6 where the 3 was
and a 5 where the 2 was.
"""
import os
import struct
import sys

sys.path.insert(0, os.path.dirname(__file__))
import gendata                                      # noqa: E402
import gensprites                                   # noqa: E402
from cpc import initial_memory                      # noqa: E402
from cpcdsk import read_dsk                         # noqa: E402

COLUMNS = 64
SIZES = {1: 5, 2: 5, 3: 2, 4: 4, 5: 5, 6: 2}


def read(path):
    d, out, o = open(path, 'rb').read(), [], 0
    while o < len(d):
        n = d[o] | d[o + 1] << 8
        c, cmds, i = d[o + 2:o + 2 + n], [], 0
        while c[i]:
            cmds.append(tuple(c[i:i + SIZES[c[i]]]))
            i += SIZES[c[i]]
        out.append(cmds)
        o += 2 + n
    return out


def write(path, passes):
    with open(path, 'wb') as f:
        for cmds in passes:
            c = bytes(b for cmd in cmds for b in cmd) + b'\0'
            f.write(struct.pack('<H', len(c)) + c)


def rect_of(sp):
    def rect(s, x, y):
        dx, dy, w, h, _ = sp[s]
        c = (x >> 1) + dx
        if not w or c >= COLUMNS:
            return None
        return c, y + dy, min(w, COLUMNS - c), h
    return rect


def box(a, b):
    if not a or not b:
        return a or b
    x, y = min(a[0], b[0]), min(a[1], b[1])
    return x, y, max(a[0] + a[2], b[0] + b[2]) - x, max(a[1] + a[3], b[1] + b[3]) - y


def meet(a, b):
    return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]


def recast(passes, rect, hybrid, eights=False):
    drawn = {}                                      # slot: its rectangle on the screen
    out, xored = [], 0
    for cmds in passes:
        new = {}                                    # slot: its new rectangle (None: gone or blank)
        for cmd in cmds:
            if cmd[0] == 2:
                new[cmd[1]] = rect(*cmd[2:])
            elif cmd[0] == 3:
                new[cmd[1]] = None
        boxes = {s: box(drawn.get(s), new.get(s, drawn.get(s))) for s in set(drawn) | set(new)}
        boxes = {s: b for s, b in boxes.items() if b}
        touch = {s for s in boxes if any(t != s and meet(boxes[s], boxes[t]) for t in boxes)} if hybrid else None
        if hybrid and eights:
            small = [r for c in cmds if c[0] == 4 for r in [rect(*c[1:])] if r]
            touch |= {s for s in boxes if any(meet(boxes[s], r) for r in small)}
        xor = (lambda s: s in touch) if hybrid else (lambda s: True)
        cast = []
        for cmd in cmds:
            k = cmd[0]
            if k == 1:
                if not xor(cmd[1]):
                    cast.append(cmd)
            elif k == 2:
                cast.append((5,) + cmd[1:] if xor(cmd[1]) else cmd)
                xored += xor(cmd[1])
            elif k == 3:
                cast.append((6, cmd[1]) if xor(cmd[1]) else cmd)
                xored += xor(cmd[1])
            else:
                cast.append(cmd)
        out.append(cast)
        for s, r in new.items():
            if r:
                drawn[s] = r
            else:
                drawn.pop(s, None)
    return out, xored


def main():
    mode, src, dst = sys.argv[1:4]
    assert mode in ('xor', 'hybrid', 'hybrid8')
    sp = gensprites.sprites(initial_memory(), gendata.pairs(read_dsk(gendata.DSK)))
    passes = read(src)
    out, xored = recast(passes, rect_of(sp), mode != 'xor', mode == 'hybrid8')
    write(dst, out)
    plots = sum(1 for cmds in passes for c in cmds if c[0] in (2, 3))
    print(f'{len(out)} passes: {xored} of {plots} large plots XORed')


if __name__ == '__main__':
    main()
