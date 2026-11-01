"""Every graphic in the CPC original as PNGs: the sprites, the dots, the font, the block sets, the zone objects, the
zones' backgrounds, the screens drawn by scripts and the loading screen. From the disc (docs/exolon.dsk), as
docs/cpc-graphics.md and docs/cpc-zones.md describe them; written to assets/ (git-ignored, as build/ is).

    .venv/bin/python tools/extract_graphics.py [out]

Each PNG is indexed, a pixel a CPC pixel: MODE 0's pixels are twice as wide as tall, so the images look narrow.
The palette is the game's 16 inks (&3EF0), index = pen. Sprites are XORed, so their pen 0 is transparent; blocks,
objects and screens are stored, so pen 0 is black (an object's cells that no block covers are index 16,
transparent). The loading screen is MODE 1 in the BASIC loader's four inks.
"""
import os
import sys

import z80
from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
import zonemodel                                        # noqa: E402
from cpc import HWRGB, initial_memory, mode0_pens       # noqa: E402
from cpcdsk import read_dsk                             # noqa: E402
from gendata import DSK                                 # noqa: E402

OUT = os.path.join(os.path.dirname(__file__), '..', 'assets')
INKS = 0x3EF0
CLEAR = 16                                              # the objects' transparent index

# the sprites: (folder, address, frames, bytes across, lines, names by frame)
SPRITES = [
    ('sprites32', 0x93CD, 25, 6, 32,
     ['walk'] * 3 + ['walk_jump', 'walk', 'walk_stand', 'walk', 'walk', 'walk', 'walk_fall', 'duck', 'die'] +
     ['suit_walk'] * 3 + ['suit_walk_jump', 'suit_walk', 'suit_walk_stand', 'suit_walk', 'suit_walk', 'suit_walk',
                          'suit_walk_fall', 'suit_duck', 'suit_die'] + ['popup']),
    ('sprites16', 0xA68D, 45, 4, 16,
     ['blank'] + ['alien_green'] * 4 + ['explosion'] * 5 + ['homing_missile'] * 2 + ['title_twinkle'] * 4 +
     ['alien_cyan_ball'] * 4 + ['alien_striped_ball'] * 4 + ['alien_white_ship'] * 4 + ['arc'] * 5 +
     ['unused_arc'] * 3 + ['timeout_missile'] + ['alien_cyan_ship'] * 4 + ['alien_yellow_fish'] * 4),
    ('sprites8', 0x921D, 9, 3, 8,                       # 48 bytes a frame: the even-x copy, then the odd
     ['grenade_right', 'grenade_left', 'debris', 'small_explosion', 'small_explosion', 'small_explosion', 'blank',
      'spore', 'launcher_missile']),
]

# the block sets, end to end from &6F8D to &921C (docs/cpc-zones.md): (address, blocks, name)
SETS = [(0x6F8D, 34, ''), (0x71AD, 42, ''), (0x744D, 20, ''), (0x758D, 32, ''), (0x778D, 20, ''), (0x78CD, 20, ''),
        (0x7A0D, 31, ''), (0x7BFD, 42, ''), (0x7E9D, 12, ''), (0x7F5D, 8, '_pickups'), (0x7FDD, 20, ''),
        (0x811D, 25, ''), (0x82AD, 18, ''), (0x83CD, 29, ''), (0x859D, 22, ''), (0x86FD, 50, '_logo'),
        (0x8A1D, 3, ''), (0x8A4D, 19, ''), (0x8B7D, 29, ''), (0x8D4D, 17, ''), (0x8E5D, 8, '_bonus'),
        (0x8EDD, 21, ''), (0x902D, 19, ''), (0x915D, 12, '_bonus_border')]
FONT = 0x6BDD                                           # characters &20-&5A, a block each
STAR, BARRIER = 0x302E, 0x38E5                          # the star's block (byte 8 set per star), the barrier's
OBJECTS = 62                                            # the object scripts, a word each at &1305
OBJECT_NAMES = {19: '_ammo_pickup', 20: '_grenade_pickup'}  # (code draws them, from &2661 and &26B7)

# the screens drawn by the interpreter (&3CDD): (name, script, the caller that runs it)
SCREENS = [('title', 0x0174, 0x0144), ('define_keys', 0x0428, 0x02C9), ('high_scores', 0x051A, 0x04DE),
           ('status_rows', 0x07A1, 0x078F), ('game_over', 0x2D57, 0x2D1B), ('name_entry', 0x2E59, 0x2DD2),
           ('bonus', 0x367A, 0x3612), ('congratulations', 0x3758, 0x3593), ('bravery_bonus', 0x380B, 0x353F)]
LOGO = 0x0491                                           # the EXOLON logo's script, run by the title's

# the dots, code immediates: the laser bolt (&10F5, even x: 4 pixels on a line), a gun's shot (&1D9A: 2 lines)
LASER = [0x4D, 0x8E]
SHOT = [0x8A, 0x88]

# the loading screen: EXOLON.SCR unpacks itself (&8000) to &4000 for FADEIN.BIN to copy to &C000 in MODE 1
# (EXOLON.LDR patches &8026); the BASIC loader set INK 0,0: INK 1,6: INK 2,18: INK 3,26 (firmware colours)
LOAD_INKS = [0, 6, 18, 26]


def palette(mem):
    return [HWRGB[mem[INKS + i]] for i in range(16)]


def pens(data, w, h):
    """MODE 0 bytes (w a line, h lines) as rows of pens, 2w across."""
    return [[p for x in range(w) for p in mode0_pens(data[y * w + x])] for y in range(h)]


def save(path, rows, rgb, transparent=None):
    img = Image.new('P', (len(rows[0]), len(rows)))
    img.putpalette([c for col in rgb for c in col])
    img.putdata([p for row in rows for p in row])
    os.makedirs(os.path.dirname(path), exist_ok=True)
    if transparent is None:
        img.save(path)
    else:
        img.save(path, transparency=transparent)


def strip(blocks):
    """16-byte blocks (2 bytes x 8 lines) side by side, as rows of pens."""
    cells = [pens(b, 2, 8) for b in blocks]
    return [[p for c in cells for p in c[y]] for y in range(8)]


def sprites(mem, rgb, out):
    n = 0
    for folder, addr, frames, w, h, names in SPRITES:
        size = w * h * (2 if folder == 'sprites8' else 1)
        for f in range(frames):
            a = addr + size * f
            save(os.path.join(out, folder, f'{f:02}_{names[f]}.png'), pens(mem[a:a + w * h], w, h), rgb, 0)
            n += 1
    # 8-line frame 7's odd-x copy is a smaller picture (the spore pulses); the others' are the even shifted
    a = 0x921D + 48 * 7 + 24
    save(os.path.join(out, 'sprites8', '07_spore_pulse.png'), pens(mem[a:a + 24], 3, 8), rgb, 0)
    laser = [p for b in LASER for p in mode0_pens(b)]
    save(os.path.join(out, 'dots', 'laser_bolt.png'), [laser], rgb, 0)
    save(os.path.join(out, 'dots', 'gun_shot.png'), [[mode0_pens(b)[0]] for b in SHOT], rgb, 0)
    return n + 3


def blocks(mem, rgb, out):
    for addr, n, name in SETS:
        save(os.path.join(out, 'blocks', f'set_{addr:04X}{name}.png'),
             strip([mem[addr + 16 * b:addr + 16 * b + 16] for b in range(n)]), rgb)
    font = [mem[FONT + 16 * c:FONT + 16 * c + 16] for c in range(0x5B - 0x20)]
    save(os.path.join(out, 'font.png'), strip(font), rgb)
    stars = []
    for p in range(1, 8):                               # the star's pen in byte 8's right pixel: bits 6, 2, 4
        b = bytearray(mem[STAR:STAR + 16])
        b[8] = (p & 1) << 6 | (p >> 1 & 1) << 2 | (p >> 2 & 1) << 4
        stars.append(b)
    save(os.path.join(out, 'blocks', 'stars.png'), strip(stars), rgb)
    save(os.path.join(out, 'blocks', 'barrier.png'), strip([mem[BARRIER:BARRIER + 16]]), rgb)
    return len(SETS) + 3


class Canvas(zonemodel.Zone):
    """The interpreter onto an unbounded grid of cells (the last block stored in a cell wins), for the objects."""

    def __init__(self, mem):
        super().__init__(mem)
        self.cells = {}

    def plot(self, row, col, data, mode, b7=0, ba=1, what=None):
        self.cells[(row - 128, col - 128)] = bytes(data)     # (the script starts at 128, 128)
        return True


def assemble(mem, script, clear):
    """A script's blocks, cropped to the cells it covers, as rows of pens (clear where no block is), or None."""
    c = Canvas(mem)
    c.run(script, 128, 128, {'set': zonemodel.FONT, 'mode': 0, 'b7': 0, 'ba': 1})
    if not c.cells:
        return None
    rs, cs = [r for r, _ in c.cells], [k for _, k in c.cells]
    r0, c0 = min(rs), min(cs)
    rows = [[clear] * 4 * (max(cs) - c0 + 1) for _ in range(8 * (max(rs) - r0 + 1))]
    for (r, k), data in c.cells.items():
        for y, line in enumerate(pens(data, 2, 8)):
            rows[8 * (r - r0) + y][4 * (k - c0):4 * (k - c0) + 4] = line
    return rows


def objects(mem, rgb, out):
    """Each object's script that draws something: 18, 41, 48, 49 and 51 are empty (&FF) and 22 and 39 only mark
    their cell (docs/cpc-objects.md)."""
    n = 0
    for obj in range(OBJECTS):
        rows = assemble(mem, zonemodel.word(mem, zonemodel.SCRIPTS + 2 * obj), CLEAR)
        if rows:
            save(os.path.join(out, 'objects', f'object_{obj:02}{OBJECT_NAMES.get(obj, "")}.png'), rows,
                 rgb + [(0, 0, 0)], CLEAR)
            n += 1
    return n


def screen_rows(screen, lines):
    return pens(screen, 64, lines)


def zones(mem, rgb, out):
    for zone in range(125):
        z = zonemodel.build(mem, zone)
        save(os.path.join(out, 'zones', f'zone_{zone:03}.png'), screen_rows(z.screen, 8 * zonemodel.ROWS), rgb)
    return 125


def screens(mem, rgb, out):
    st = lambda: {'set': zonemodel.FONT, 'mode': 0, 'b7': 0, 'ba': 1}   # noqa: E731
    for name, script, _ in SCREENS:
        z = zonemodel.Zone(mem)
        z.run(script, 0, 0, st())
        save(os.path.join(out, 'screens', f'{name}.png'), screen_rows(z.screen, 192), rgb)
    rows = assemble(mem, LOGO, 0)                       # the logo alone, cropped to its cells
    save(os.path.join(out, 'screens', 'logo.png'), rows, rgb)
    return len(SCREENS) + 1


def loading(files, out):
    mem = bytearray(65536)
    scr = files['EXOLON.SCR']['data']
    mem[0x8000:0x8000 + len(scr)] = scr
    mem[0x8026:0x8028] = b'\x00\x40'                    # EXOLON.LDR: LD HL,&4000: LD (&8026),HL
    ret = 0xFFF0
    mem[0xBFFE:0xC000] = bytes((ret & 0xFF, ret >> 8))
    z = z80.Z80Machine()
    z.set_memory_block(0, mem)
    z.pc, z.sp = 0x8000, 0xBFFE
    z.set_breakpoint(ret)
    for _ in range(100):
        z.ticks_to_stop = 1 << 22
        if z.run() & z._BREAKPOINT_HIT and z.pc == ret:
            break
    else:
        raise RuntimeError('EXOLON.SCR never returned')
    m = z.memory
    rows = []
    for y in range(200):                                # MODE 1: 80 bytes a line; pen bits 7-i and 3-i
        a = 0x4000 + (y & 7) * 0x800 + (y >> 3) * 80
        rows.append([(m[a + x] >> (7 - i) & 1) | (m[a + x] >> (3 - i) & 1) << 1 for x in range(80) for i in range(4)])
    levels = [(n // 3 % 3, n // 9, n % 3) for n in LOAD_INKS]                  # firmware colour: 9G + 3R + B
    save(os.path.join(out, 'screens', 'loading.png'), rows, [tuple((0, 128, 255)[g] for g in c) for c in levels])
    return 1


README = """# Exolon (CPC) graphics

Extracted from `docs/exolon.dsk` by `tools/extract_graphics.py`. Not committed: run the script to remake them.

- Indexed PNGs, a pixel a CPC pixel. MODE 0's pixels are twice as wide as tall, so everything looks narrow;
  scale the width by 2 to see it as the CPC shows it.
- Palette: the game's 16 inks, index = pen. Sprites have pen 0 transparent (they're XORed); blocks, objects and
  screens have it black. In an object, index 16 (transparent) is a cell no block covers.

| Folder | What |
|---|---|
| `sprites32/` | 25 frames, 12 x 32: the player (0-11; 12-23 in the suit), the popup (24) |
| `sprites16/` | 45 frames, 8 x 16: aliens, explosions, missiles, the arc, the title's twinkles |
| `sprites8/` | 9 frames, 6 x 8 (even x): grenades, debris, small explosions, the spore, the launcher missile; `07_spore_pulse` is frame 7's odd-x copy, a different picture |
| `dots/` | the laser bolt (4 x 1) and a gun's shot (1 x 2) |
| `blocks/` | every block set, a strip of 4 x 8 blocks named by its address; the stars (pens 1-7), the barrier |
| `font.png` | characters `&20`-`&5A`, 4 x 8 each |
| `objects/` | the zone objects, assembled from their scripts (18, 41, 48, 49 and 51 are empty; 22 and 39 only mark a cell) |
| `zones/` | the 125 zones' backgrounds, 128 x 176 (the stars are random: generator seed 0) |
| `screens/` | the screens drawn by scripts (on a blank screen, without what code adds), the logo, the loading screen (MODE 1, 320 x 200) |

What each frame and set is: `docs/cpc-graphics.md`, `docs/cpc-zones.md`.
"""


def main(out=OUT):
    mem = initial_memory()
    rgb = palette(mem)
    n = sprites(mem, rgb, out) + blocks(mem, rgb, out) + objects(mem, rgb, out) + zones(mem, rgb, out)
    n += screens(mem, rgb, out) + loading(read_dsk(DSK), out)
    with open(os.path.join(out, 'README.md'), 'w') as f:
        f.write(README)
    print(f'{n} PNGs in {os.path.normpath(out)}')


if __name__ == '__main__':
    main(*sys.argv[1:])
