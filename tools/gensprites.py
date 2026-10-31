"""The sprites for the BBC (P9, D30): every frame of the CPC's three sprite sets, trimmed to its bounding rectangle
on byte boundaries for each pixel shift, dithered to MODE 2, column by column.

    .venv/bin/python tools/gensprites.py build/gen          # writes sprites.bin and sprites.6502

For now every sprite is kept raw in the data's bank, but for those OMITTED (blank, SprW 0): the suit's frames,
the title's twinkles and the three never seen, none of which the plot logs draw. Packs unpacked between screens
replace this (P5, P11). The six tables (SprW, SprH, SprDX, SprDY, SprLo, SprHi) are a page each, so no indexed
read of them crosses a page, with whole sprites in the 98 bytes after each of the first five (layout()). The 8-line
set's data isn't kept: the debris is compiled for each even phase (debris_code), the rest as two copies each
(xor8_code), in build/gen/xor8code.6502 for main RAM.

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
Sprite8First = 140


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
    if shifted:                                     # the 8-line set untrimmed at its top and left (xor8)
        k0, y0, y1 = 0, 0, hgt - 1
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


def debris_code(sp):
    """Debris (frame 2, sprites 144 and 145) compiled for each even phase: XOR immediates through dt (the
    cell row's line 0 at the column) and db (dt + 512), each byte's Y its own (INY where it follows on)."""
    out = ['', '\\\\ debris, compiled (sprites.6502\'s debris_xor)']
    names = []
    for p in (0, 2, 4, 6):
        for s in (0, 1):
            dx, dy, w, h, d = sp[144 + s]
            assert dx == 0 and dy == 0 and w == 3 and h == 8
            todo = []
            for k in range(3):
                for j in range(8):
                    v = d[8 * k + j]
                    if v:
                        todo.append((8 * k + p + j, 'dt', v) if p + j < 8 else (8 * k + p + j - 8, 'db', v))
            todo.sort()
            name = f'debris_p{p}_s{s}'
            names.append(name)
            out.append(f'.{name}')
            y = None
            for yy, ptr, v in todo:
                out.append('    INY' if y is not None and yy == y + 1 else f'    LDY #{yy}')
                out.append(f'    LDA ({ptr}),Y:EOR #&{v:02X}:STA ({ptr}),Y')
                y = yy
            out.append('    RTS')
    out.append('DebrisList = {' + ', '.join(names) + '}')
    out.append('SprWList = {' + ', '.join(str(x[2]) for x in sp[140:]) + '}')
    out.append('.DebLo')
    out.append('    EQUB ' + ', '.join(f'LO({n})' for n in names))
    out.append('.DebHi')
    out.append('    EQUB ' + ', '.join(f'HI({n})' for n in names))
    return out


def layout(sp):
    """Where each large sprite's data goes, as offsets from the tables' page: the six tables a page each (so no
    indexed read crosses one), the 98 bytes after each of the first five filled with whole sprites, the rest
    after the last table. (The 8-line set is compiled: xor8_code.) Returns the offsets and the gaps' sprites."""
    n = len(sp)
    order = sorted((i for i in range(Sprite8First) if sp[i][4]), key=lambda i: -len(sp[i][4]))
    offsets, gaps = [0] * n, []
    for g in range(5):
        room, pos, chosen = 256 - n, 256 * g + n, []
        if g == 0:                                  # xor8's XcSlot first (read at XcSlot - Sprite8 + sprite)
            room, pos = room - (n - Sprite8First), pos + n - Sprite8First
        for i in list(order):
            if len(sp[i][4]) <= room:
                offsets[i], pos, room = pos, pos + len(sp[i][4]), room - len(sp[i][4])
                chosen.append(i)
                order.remove(i)
        gaps.append(chosen)
    pos = 256 * 5 + n
    for i in sorted(order):
        offsets[i], pos = pos, pos + len(sp[i][4])
    blob = [i for i in sorted(order)]
    return offsets, gaps, blob


def xc_names(sp):
    """The 8-line sprites xor8_code compiles: all but the debris (frame 2) and the blank (frame 6)."""
    return [s for s in range(Sprite8First, len(sp)) if sp[s][2] and s not in (Sprite8First + 4, Sprite8First + 5)]


def xc_slot(sp):
    """xor8's XcSlot: each 8-line sprite's compiled copies, their index in XtLo and the rest (in the first sprite
    table's page, past offset 140, so XcSlot - Sprite8 indexes it in its page)."""
    slot = {s: 8 * i for i, s in enumerate(xc_names(sp))}
    return ['.XcSlot                                 ; xor8: an 8-line sprite\'s compiled copies, their index in XtLo...',
            '    EQUB ' + ', '.join(str(slot.get(s, 0)) for s in range(Sprite8First, len(sp))),
            'ASSERT HI(XcSlot - Sprite8) == HI(XcSlot + SpriteCount - Sprite8 - 1), "XcSlot read in its page"']


def xor8_code(sp):
    """The 8-line sprites but the debris and the blank, compiled for xor8: XOR immediates, zero bytes left out.
    With xt at the sprite's top-left byte on the screen and xb = xt + 504 (the cell row below, 8 lines back),
    the sprite's column k line j is at Y = 8k + j through xt if its screen line is in the top band (j < 8 -
    phase), else through xb. So each sprite has two copies: lines 7 to 0 through xt, then lines 0 to 7 through
    xb, each to an RTS; a phase p runs the first from line 7 - p (XtLo, XtHi) and the second from line 8 - p
    (XbLo, XbHi)."""
    names = xc_names(sp)
    out = ["\\\\ xor8code.6502 - made by tools/gensprites.py: the 8-line sprites but the debris and the blank,",
           "\\\\ compiled for sprites.6502's xor8 (gensprites' xor8_code says how).", ""]
    tents, bents = [], []
    for s in names:
        dx, dy, w, h, d = sp[s]
        b = [(k, j, d[8 * k + j]) for k in range(w) for j in range(8) if d[8 * k + j]]
        top = sorted(b, key=lambda e: (-e[1], e[0]))
        low = sorted(b, key=lambda e: (e[1], e[0]))
        out += [f'.xc{s}']
        out += [f'    LDY #{8 * k + j}:LDA (xt),Y:EOR #&{v:02X}:STA (xt),Y' for k, j, v in top]
        out += ['    RTS', f'.xc{s}b']
        out += [f'    LDY #{8 * k + j}:LDA (xb),Y:EOR #&{v:02X}:STA (xb),Y' for k, j, v in low]
        out += ['    RTS']
        for p in range(8):
            t = f'xc{s} + {8 * sum(1 for e in b if e[1] > 7 - p)}'
            lw = f'xc{s}b + {8 * sum(1 for e in b if e[1] < 8 - p)}'
            tents.append(t); bents.append(lw)
    out += ['', 'XcTopEntries = {' + ', '.join(tents) + '}',
            'XcLowEntries = {' + ', '.join(bents) + '}',
            '.XtLo                                   ; the top band\'s entry for each phase',
            '    EQUB LO(XcTopEntries)',
            '.XtHi',
            '    EQUB HI(XcTopEntries)',
            '.XbLo                                   ; the band below\'s',
            '    EQUB LO(XcLowEntries)',
            '.XbHi',
            '    EQUB HI(XcLowEntries)', '']
    return out


def main(out):
    m = initial_memory()
    pairs = gendata.pairs(read_dsk(gendata.DSK))
    sp = sprites(m, pairs)
    os.makedirs(out, exist_ok=True)
    offsets, gaps, blob = layout(sp)
    with open(os.path.join(out, 'sprites.bin'), 'wb') as f:
        f.write(b''.join(sp[i][4] for i in blob))
    n = len(sp)
    lines = ['\\\\ sprites.6502 - made by tools/gensprites.py from docs/exolon.dsk: the sprites, trimmed and dithered,',
             '\\\\ and their tables (tools/gensprites.py says how they\'re numbered and placed).', '',
             f'SpriteCount = {n}', 'Sprite32 = 0', 'Sprite16 = 50', f'Sprite8 = {Sprite8First}',
             f'SpriteMaxW = {max(s[2] for s in sp)}', f'SpriteMaxH = {max(s[3] for s in sp)}', '',
             'ASSERT LO(P%) == 0, "the sprite tables: each in its own page"', '.SpriteTables']
    tables = (('SprW', [s[2] for s in sp]), ('SprH', [s[3] for s in sp]), ('SprDX', [s[0] for s in sp]),
              ('SprDY', [s[1] for s in sp]),
              ('SprLo', [f'LO(SpriteTables + {o})' for o in offsets]),
              ('SprHi', [f'HI(SpriteTables + {o})' for o in offsets]))
    used = 0
    for t, (label, vals) in enumerate(tables):
        lines += [f'.{label}', *['    EQUB ' + ', '.join(str(v) for v in vals[i:i + 10]) for i in range(0, n, 10)]]
        if t == 0:
            lines += xc_slot(sp)
            used += n - Sprite8First
        if t < len(gaps):
            data = b''.join(sp[i][4] for i in gaps[t])
            used += len(data)
            lines += [f'    \\\\ sprites {", ".join(str(i) for i in gaps[t])}',
                      *['    EQUB ' + ', '.join(f'&{b:02X}' for b in data[i:i + 16]) for i in range(0, len(data), 16)],
                      f'    SKIP {256 - n - len(data) - (n - Sprite8First if t == 0 else 0)}']
    lines += ['.SpriteData', '    INCBIN "sprites.bin"',
              f'ASSERT SpriteData == SpriteTables + {256 * 5 + n}, "the sprites after the tables where gensprites put them"',
              '']
    lines += debris_code(sp)
    with open(os.path.join(out, 'sprites.6502'), 'w') as f:
        f.write('\n'.join(lines))
    with open(os.path.join(out, 'xor8code.6502'), 'w') as f:
        f.write('\n'.join(xor8_code(sp)))
    total = sum(len(s[4]) for s in sp[:Sprite8First])
    print(f'{n} sprites, {total} bytes of data ({used} in the tables\' pages, {5 * (256 - n) - used} spare there)')


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'build/gen')
