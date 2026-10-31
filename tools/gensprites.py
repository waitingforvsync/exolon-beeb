"""The sprites for the BBC (P9, D30): every frame of the CPC's three sprite sets, trimmed to its bounding rectangle
on byte boundaries for each pixel shift, dithered to MODE 2, column by column.

    .venv/bin/python tools/gensprites.py build/gen          # writes sprites.bin and sprites.6502

For now every sprite is kept raw in the data's bank, but for those OMITTED (blank, SprW 0): the suit's frames,
the title's twinkles and the three never seen, none of which the plot logs draw. Packs unpacked between screens
replace this (P5, P11).

A sprite is one shift of one frame, numbered:
- 0-49: the 32-line set (the CPC's &93CD: the player's 24 frames facing right, then the popup), frame f's even
  shift 2f and odd 2f + 1;
- 50-139: the 16-line set (&A68D, 45 frames), frame f at 50 + 2f (even) and 51 + 2f (odd);
- 140-157: the 8-line set (&921D, 9 frames, stored by the CPC as even and odd copies), frame f's at 140 + 2f and
  141 + 2f.
An object at x (MODE 0 pixels, 0-127) uses its frame's shift x AND 1, and its sprite's bytes go from byte
column (x >> 1) + SprDX, line y + SprDY, SprW bytes across and SprH lines down. The data is in the screen's own
layout for a character row: band j (the sprite's lines 8j to 8j + 7) is SprW columns of 8 bytes each, the
lines past SprH 0, so a band's column k line l is at 8k + l as on the screen; bands follow each other, 8 × SprW
apart. A pixel is its pen's BBC colour, or its pair's by the pixel's place in the sprite (so the dither moves
with it); pen 0 is 0, and no sprite pixel has bit 3 (P10). A blank frame has SprW 0.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cpc import initial_memory, mode0_pens          # noqa: E402
from cpcdsk import read_dsk                         # noqa: E402
import gendata                                      # noqa: E402

OMITTED = {('Sprite32', f) for f in range(12, 24)} | {('Sprite16', f) for f in (12, 13, 14, 15, 33, 34, 35)}
SETS = [('Sprite32', 0x93CD, 25, 6, 32, False), ('Sprite16', 0xA68D, 45, 4, 16, False),
        ('Sprite8', 0x921D, 9, 3, 8, True)]


def sprite(pens, s, pairs, shifted):
    """One shift of a frame: (dx, dy, w, h, data). pens[y][x] is the frame's pixels; s the shift; shifted means
    the frame's pixels are already shifted by s (the 8-line set's odd copies), so they're placed as they are."""
    hgt, wid = len(pens), len(pens[0])
    opaque = [(x, y) for y in range(hgt) for x in range(wid) if pens[y][x]]
    if not opaque:
        return 0, 0, 0, 0, b''
    place = 0 if shifted else s                     # where pixel x of the frame lands: x + place
    k0 = (min(x for x, _ in opaque) + place) >> 1
    k1 = (max(x for x, _ in opaque) + place) >> 1
    y0 = min(y for _, y in opaque)
    y1 = max(y for _, y in opaque)
    h = y1 - y0 + 1
    data = bytearray()
    for band in range((h + 7) // 8):
        for k in range(k0, k1 + 1):
            for line in range(8):
                y = y0 + 8 * band + line
                if y > y1:
                    data.append(0)
                    continue
                colours = []
                for p in (2 * k - place, 2 * k + 1 - place):
                    pen = pens[y][p] if 0 <= p < wid else 0
                    sx = p - (s if shifted else 0)  # the pixel's place in the unshifted sprite: its dither
                    colours.append(pairs[pen][(sx + y) & 1])
                data.append(gendata.mode2_byte(colours[0], colours[1]))
    return k0, y0, k1 - k0 + 1, h, bytes(data)


def sprites(m, pairs):
    out = []
    for name, base, n, w, h, copies in SETS:
        for f in range(n):
            for s in (0, 1):
                if (name, f) in OMITTED:
                    out.append((0, 0, 0, 0, b''))
                    continue
                if copies:
                    a = base + 48 * f + 24 * s
                    pens = [[p for b in m[a + y * w:a + y * w + w] for p in mode0_pens(b)] for y in range(h)]
                else:
                    a = base + f * w * h
                    pens = [[p for b in m[a + y * w:a + y * w + w] for p in mode0_pens(b)] for y in range(h)]
                out.append(sprite(pens, s, pairs, copies))
    return out


def main(out):
    m = initial_memory()
    pairs = gendata.pairs(read_dsk(gendata.DSK))
    sp = sprites(m, pairs)
    os.makedirs(out, exist_ok=True)
    data, offsets = bytearray(), []
    for dx, dy, w, h, d in sp:
        offsets.append(len(data))
        data += d
    with open(os.path.join(out, 'sprites.bin'), 'wb') as f:
        f.write(data)
    n = len(sp)
    lines = ['\\\\ sprites.6502 - made by tools/gensprites.py from docs/exolon.dsk: the sprites, trimmed and dithered,',
             '\\\\ and their tables (tools/gensprites.py says how they\'re numbered).', '',
             f'SpriteCount = {n}', 'Sprite32 = 0', 'Sprite16 = 50', 'Sprite8 = 140',
             f'SpriteMaxW = {max(s[2] for s in sp)}', f'SpriteMaxH = {max(s[3] for s in sp)}', '']
    for label, vals in (('SprW', [s[2] for s in sp]), ('SprH', [s[3] for s in sp]),
                        ('SprDX', [s[0] for s in sp]), ('SprDY', [s[1] for s in sp])):
        lines += [f'    INPAGE {n}', f'.{label}',
                  *['    EQUB ' + ', '.join(str(v) for v in vals[i:i + 20]) for i in range(0, n, 20)]]
    lines += [f'    INPAGE {n}', '.SprLo',
              *['    EQUB ' + ', '.join(f'LO(SpriteData + {o})' for o in offsets[i:i + 10]) for i in range(0, n, 10)],
              f'    INPAGE {n}', '.SprHi',
              *['    EQUB ' + ', '.join(f'HI(SpriteData + {o})' for o in offsets[i:i + 10]) for i in range(0, n, 10)],
              '.SpriteData', '    INCBIN "sprites.bin"', '']
    with open(os.path.join(out, 'sprites.6502'), 'w') as f:
        f.write('\n'.join(lines))
    print(f'{n} sprites, {len(data)} bytes of data')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'build/gen')
