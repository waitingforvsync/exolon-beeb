"""The data the BBC build takes from the CPC disc: for now, each pen's dithered MODE 2 bytes (P4).

    .venv/bin/python tools/gendata.py build/gen

Each of the CPC's 16 inks (the game's palette, at &3EF0) goes to a BBC colour, or to a checkerboard of the
two BBC colours whose average it is: of the pairs that average to it, the two closest in brightness (Chase
H.Q.'s D7, Rec. 601 luma). A pixel at (x, y) shows the pair's first colour where x + y is even, the second
where it's odd. Writes gen/pens.6502: PenEven and PenOdd, a byte of each pen on even and odd lines.
"""
import os
import sys
from itertools import combinations_with_replacement

sys.path.insert(0, os.path.dirname(__file__))
from cpc import LEVELS                                  # noqa: E402
from cpcdsk import read_dsk                             # noqa: E402

DSK = os.path.join(os.path.dirname(__file__), '..', 'docs', 'exolon.dsk')
INKS = 0x3EF0                                           # the game's 16 inks, set by &3E90
LUMA = (0.299, 0.587, 0.114)
NAMES = ['black', 'red', 'green', 'yellow', 'blue', 'magenta', 'cyan', 'white']


def bbc_bits(c):
    """A BBC colour's guns, R G B."""
    return (c & 1, c >> 1 & 1, c >> 2 & 1)


def luma(c):
    return sum(w * b for w, b in zip(LUMA, bbc_bits(c)))


def pair_for(hw):
    """A CPC hardware colour's BBC pair: the darker first."""
    want = LEVELS[hw]
    best = None
    for a, b in combinations_with_replacement(range(8), 2):
        if all(x + y == w for x, y, w in zip(bbc_bits(a), bbc_bits(b), want)):
            key = (abs(luma(a) - luma(b)), a, b)
            best = key if best is None or key < best else best
    _, a, b = best
    return (a, b) if luma(a) <= luma(b) else (b, a)


def right_pixel(c):
    return (c & 1) | (c & 2) << 1 | (c & 4) << 2 | (c & 8) << 3


def mode2_byte(left, right):
    return right_pixel(left) << 1 | right_pixel(right)


def inks(files):
    d = files['EXOLON.1']['data']
    return [d[INKS - 0x0100 + p] for p in range(16)]


def pairs(files):
    return [pair_for(hw) for hw in inks(files)]


def main(out):
    files = read_dsk(DSK)
    ps = pairs(files)
    os.makedirs(out, exist_ok=True)
    lines = ['\\\\ pens.6502 - made by tools/gendata.py from docs/exolon.dsk: each CPC pen dithered (P4)',
             '\\\\',
             '\\\\   pen  ink  BBC']
    for p, (hw, (a, b)) in enumerate(zip(inks(files), ps)):
        lines.append(f'\\\\   {p:3}  {hw:3}  {NAMES[a] if a == b else NAMES[a] + " / " + NAMES[b]}')
    lines += ['',
              '.PenEven                                ; pen p on an even line: the pair\'s first on the left',
              '    EQUB ' + ', '.join(f'&{mode2_byte(a, b):02X}' for a, b in ps),
              '.PenOdd                                 ; and on an odd line: its second',
              '    EQUB ' + ', '.join(f'&{mode2_byte(b, a):02X}' for a, b in ps),
              '']
    with open(os.path.join(out, 'pens.6502'), 'w') as f:
        f.write('\n'.join(lines))


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'build/gen')
