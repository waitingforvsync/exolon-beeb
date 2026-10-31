"""A model of how the CPC original draws a zone's background, from its data alone (docs/cpc-zones.md).

It runs the zone set-up (&126E) as the spec describes it: the cell maps cleared, the stars, the placements'
object scripts through the block interpreter (&3CDD), the special cells listed (&1BE0) and the force field's
beam (&38AD). Out come the tile map (each cell's block, or a star), the two cell maps (&B700, &BA00), the
playfield's bytes and a PNG in the CPC's palette (the inks at &3EF0).

    .venv/bin/python tools/zonemodel.py 0 build/zone0.png          # zone 0, the generator's seed 0
    .venv/bin/python tools/zonemodel.py 0 out.png --seed 0x1234    # with the seed (&3B02) found at &126E
    .venv/bin/python tools/zonemodel.py --check [first-last] [--seeds] [--png]
                                        # zones against the CPC's own drawing; --seeds pokes a different
                                        # seed for each zone; --png keeps both screens in work/zones/png

The stars are random, so the model needs the generator's seed as the set-up found it. --check takes it from the
harness at &126E for each zone, runs on to the first pass (&06C3) and compares the playfield (rows 0-21) byte
for byte, leaving out the bytes a sprite plotter (&07D9, &0B5F, &2020) wrote during the set-up.

    import zonemodel
    z = zonemodel.build(mem, zone, seed)   # mem: the 64K image (cpc.initial_memory())
    z.tiles[row][col]                      # (set, block), ('star', byte) or None; rows 0-21 the playfield
    z.screen                               # 64 bytes a line, 192 lines
    z.b700, z.ba00                         # the cell maps, 32 a row
"""
import os
import sys

from PIL import Image

sys.path.insert(0, os.path.dirname(__file__))
from cpc import FRAME_T, HWRGB, initial_memory, mode0_pens      # noqa: E402

ZONES = 0x490E                      # word table, 125 zones: placement lists (row, column, object), &FF ends
SCRIPTS = 0x1305                    # word table, 62 objects: block scripts
FONT = 0x69DD                       # the default block set (the font: characters &20-&5F used)
INKS = 0x3EF0                       # the 16 hardware inks
ROWS, COLS = 22, 32                 # the playfield's cells; rows 22-23 are the status
LISTS = 0x1C42                      # 6 bytes a cell value v at LISTS + 6v (v = 2-17): list, pointer, stride, value
BEAM_LIST = 0x38E2                  # the list of value 17: the force field's emitter (column, row)
BEAM_SET = 0x38E5                   # the beam's block: 55 AA on every line
STAR_LINE = 8                       # the star block (&302E) is blank but for byte 8: line 4, the left byte


def word(mem, a):
    return mem[a] | mem[a + 1] << 8


def rnd(state, a):
    """&3AE7: seed = (seed + 7) * 13, and A XOR the new seed's high byte: the caller's A goes into it."""
    s = (state[0] + 7) * 13 & 0xFFFF
    state[0] = s
    return a ^ s >> 8


def screen_index(addr):
    """A screen address (&C000 + (y & 7) * &800 + (y >> 3) * 64 + x) as y * 64 + x, or None past row 23."""
    off = addr - 0xC000
    if (off & 0x7FF) >= 64 * 24:
        return None
    return ((off >> 11) | ((off & 0x7FF) // 64) << 3) * 64 + (off & 0x7FF) % 64


class Zone:
    def __init__(self, mem):
        self.mem = mem
        self.screen = bytearray(64 * 192)
        self.maps = bytearray(0x900)                # &B700-&BFFF: &B700 map, &BA00 map, &BD00 swap table...
        self.maps[0:0x2C0] = b'\xff' * 0x2C0        # &1B69: &B700 to &FF, &1B5B: &BA00 to 0 (&2C0 bytes each)
        self.tiles = [[None] * COLS for _ in range(24)]
        self.writes = []                            # each block plotted: (row, col, set, block, mode, b7, ba)
        self.lists = {}                             # cell value (2-17) -> [(col, row)], as &1BE0 makes them
        self.stars = []
        self.beam = None

    @property
    def b700(self):
        return self.maps[0:0x2C0]

    @property
    def ba00(self):
        return self.maps[0x300:0x5C0]

    # the block plotters: &3B92 (0, store, maps), &3BDB (1, store), &3C0E (2, XOR), &3C43 (3, XOR, maps
    # cleared), &3C94 (4, as 3 with no column test). The zone set-up uses 0 and 1.

    def plot(self, row, col, data, mode, b7=0, ba=1, what=None):
        """One block of 2 bytes x 8 lines at character cell (row, col), with the Z80's arithmetic."""
        col &= 0xFF
        row &= 0xFF
        if mode in (0, 3) and col & 0x20:
            return False                            # BIT 5,E: RET NZ
        e = (col * 2) & 0xFF                        # SLA E
        d = ((row >> 2) | (row << 6)) & 0xFF        # RRCA, RRCA
        e |= d & 0xC0
        d |= 0xC0
        top = d << 8 | e
        line = 0
        while True:
            for i in (0, 1):
                idx = screen_index(d << 8 | ((e + i) & 0xFF))     # INC E / DEC E: the low byte only
                if idx is not None:
                    v = data[2 * line + i]
                    self.screen[idx] = v if mode < 2 else self.screen[idx] ^ v
            line += 1
            d += 8
            if d > 0xFF:                            # ADD A,C: JP NC, so 8 lines from &C0-&C7
                break
        self.writes.append((row, col) + (what or (None, None)) + (mode, b7, ba))
        if row < 24 and col < 32:
            self.tiles[row][col] = what
        if mode in (0, 3, 4):
            cell = (top >> 1) & 0x3FF                # SRL H: RR L: H AND 3 + &B7
            if mode == 0:
                self.maps[cell], self.maps[cell + 0x300] = b7, ba
            else:
                self.maps[cell], self.maps[cell + 0x300] = 0xFF, 0
        return True

    def block(self, bset, b):
        a = bset + ((b * 2) & 0xFF) * 8             # ADD A,A: LD L,A: H 0: ADD HL,HL x 3
        return bytes(self.mem[(a + i) & 0xFFFF] for i in range(16))

    # the interpreter, &3CDD

    def run(self, a, row, col, st):
        mem = self.mem
        d, e = row, col
        loops = []

        def put(b):
            self.plot(d, e, self.block(st['set'], b), st['mode'], st['b7'], st['ba'], (st['set'], b))

        while True:
            op = mem[a]
            a += 1
            if op < 0x61:                           # a block, then right a cell
                put(op)
                e = (e + 1) & 0xFF
            elif op < 0x90:                         # move: rows op - &78 (-23..+23), columns the next byte
                d = (d + op - 0x78) & 0xFF
                e = (e + mem[a]) & 0xFF
                a += 1
            elif op < 0xCF:                         # newline: down a row, columns op - &AF (-31..+31)
                d = (d + 1) & 0xFF
                e = (e + op - 0xAF) & 0xFF
            elif op < 0xDF:                         # the Spectrum's ink (and BRIGHT) into C: no effect
                pass
            elif op == 0xDF:                        # to (row, column)
                d, e = mem[a], mem[a + 1]
                a += 2
            elif op == 0xE0:                        # the Spectrum's attribute byte into C: no effect
                a += 1
            elif op == 0xE1:                        # loop n times (0 is 256)
                loops.append([a + 1, mem[a] or 256])
                a += 1
            elif op == 0xE2:
                loops[-1][1] -= 1
                if loops[-1][1]:
                    a = loops[-1][0]
                else:
                    loops.pop()
            elif op == 0xE3:                        # a sub-script; row and column restored after
                self.run(word(mem, a), d, e, st)
                a += 2
            elif op in (0xE4, 0xE5):                # n of block b across (E4) or down (E5)
                n, b = mem[a] or 256, mem[a + 1]
                a += 2
                for _ in range(n):
                    put(b)
                    if op == 0xE4:
                        e = (e + 1) & 0xFF
                    else:
                        d = (d + 1) & 0xFF
            elif op == 0xE6:                        # the block set (&3BA1)
                st['set'] = word(mem, a)
                a += 2
            elif op == 0xE7:                        # a blank (the font's space), then right
                self.plot(d, e, self.block(FONT, 0x20), st['mode'], st['b7'], st['ba'], (FONT, 0x20))
                e = (e + 1) & 0xFF
            elif op == 0xE8:                        # mode 0's &BA00 value (&3BD5)
                st['ba'] = mem[a]
                a += 1
            elif op == 0xE9:                        # mode 0's &B700 value (&3BCF): 0, sprites masked off
                st['b7'] = 0
            elif op == 0xEA:                        # &FF: sprites shown
                st['b7'] = 0xFF
            elif op == 0xEB:                        # this cell's &BA00 value, nothing drawn (mode 0 only)
                if st['mode'] == 0:
                    self.maps[0x300 + (((d & 31) * 32 + (e & 31)) & 0x3FF)] = mem[a]
                    self.writes.append((d, e, 'EB', mem[a], 0, None, mem[a]))
                a += 1
            else:                                   # &EC-&FF: the end
                return


def build(mem, zone, seed=0):
    """The zone's background as &126E-&12F7 draws it. seed: the generator's state (&3B02) at &126E."""
    z = Zone(mem)
    z.zone = zone
    r = [seed]
    # &2FF6: three stars a row, rows 21 up to 0, by mode 1 (stores, the maps untouched). The generator
    # returns the caller's A XOR the seed's high byte: A is &C5 the first time (left in A' by &3E0C's last
    # &3E38), then 0 for each column; &FF (the &B700 cell) for each star's first pen, then 0 for retries.
    a = 0xC5
    for b in range(ROWS, 0, -1):
        for _ in range(3):
            col, row = rnd(r, a) & 0x1F, b - 1
            a = 0
            if z.maps[row * 32 + col]:              # always so: &B700 is all &FF until the placements
                v = rnd(r, z.maps[row * 32 + col]) & 0x54
                while not v:
                    v = rnd(r, 0) & 0x54
                data = bytearray(16)
                data[STAR_LINE] = v
                z.plot(row, col, data, 1, what=('star', v))
                z.stars.append((row, col, v))
    z.seed_after = r[0]
    # the placements, &12B4-&12E4: each object's script in mode 0, &BA00 value 1, &B700 value 0
    st = {'set': FONT, 'mode': 0, 'b7': 0, 'ba': 1}
    z.placements = placements(mem, zone)
    for row, col, obj in z.placements:
        st['ba'], st['b7'] = 1, 0
        z.run(word(mem, SCRIPTS + 2 * obj), row, col, st)
    # &1BE0: cells of value 2 or more listed by value, each given its list's own value
    for cell in range(0x2C0):
        v = z.maps[0x300 + cell]
        if v >= 2:
            z.lists.setdefault(v, []).append((cell & 31, cell >> 5))
            z.maps[0x300 + cell] = mem[LISTS + 6 * v + 5]
    # &38AD: the force field, from the emitter (value 17) down to the first cell of &BA00 not 0
    if 17 in z.lists:
        col, row = z.lists[17][0]                   # the list holds one entry: the first found
        n = 0
        while True:
            row = (row + 1) & 0xFF
            z.plot(row, col, z.block(BEAM_SET, 0), 0, 0, 1, (BEAM_SET, 0))
            n += 1
            nxt = ((row + 1) & 0xFF) * 32 + col
            if (z.maps[0x300 + nxt] if nxt < 0x600 else mem[0xBA00 + nxt]):
                break
        z.beam = (z.lists[17][0], n)
    return z


def placements(mem, zone):
    a = word(mem, ZONES + 2 * zone)
    out = []
    while mem[a] != 0xFF:
        out.append((mem[a], mem[a + 1], mem[a + 2]))
        a += 3
    return out


def image(screen, inks, rows=ROWS, scale=2):
    """MODE 0 bytes (64 a line, line-major) as an image, pixels twice as wide as tall (as cpc.screen_image)."""
    rgb = [HWRGB[i] for i in inks]
    img = Image.new('RGB', (256, rows * 8))
    px = img.load()
    for y in range(rows * 8):
        for x in range(64):
            left, right = mode0_pens(screen[y * 64 + x])
            px[x * 4, y] = px[x * 4 + 1, y] = rgb[left]
            px[x * 4 + 2, y] = px[x * 4 + 3, y] = rgb[right]
    return img.resize((img.width * scale // 2, img.height * scale), Image.NEAREST)


def cpc_screen(mem, rows=24):
    """The CPC's screen as 64 bytes a line, line-major."""
    out = bytearray(rows * 8 * 64)
    for y in range(rows * 8):
        a = 0xC000 + (y & 7) * 0x800 + (y >> 3) * 64
        out[y * 64:y * 64 + 64] = mem[a:a + 64]
    return out


SPRITES = (0x07D9, 0x0B5F, 0x2020)


def harness_zone(zone, seed=None):
    """The harness started at zone (the disc's poke), run to the first pass. Returns (machine, seed at &126E,
    the screen bytes the sprite plotters wrote during the set-up as a 64 x 192 bytearray of flags). A seed
    given is poked into &3B02 at &126E (to try the stars with many seeds)."""
    from cpc import CPC
    m = CPC()
    m.mem[0x010E:0x0111] = b'\0\0\0'
    m.mem[0x12FA] = zone
    z = m.z
    inside = [False]
    touched = bytearray(64 * 192)

    def on_write(addr, v):
        m.mem[addr] = v
        if inside[0]:
            i = screen_index(addr)
            if i is not None:
                touched[i] = 1

    z.set_write_callback(on_write)
    z.mark_addrs(0xC000, 0x4000, z.WRITE_MARK)
    m.run_to(None, 100 * FRAME_T)                    # the title for 100 frames, as start_game
    m.hold({'1'})
    if not m.run_to(0x126E, 50 * FRAME_T):          # '1' held until the zone set-up starts
        raise RuntimeError(f'zone {zone}: no zone set-up')
    m.hold(set())
    if seed is not None:
        m.mem[0x3B02], m.mem[0x3B03] = seed & 0xFF, seed >> 8
    seed = word(m.mem, 0x3B02)
    while True:
        for a in SPRITES:
            z.set_breakpoint(a)
        hit = m.run_to(0x06C3, 100 * FRAME_T)
        for a in SPRITES:
            z.clear_breakpoint(a)
        if hit:
            break
        if z.pc not in SPRITES:
            raise RuntimeError(f'zone {zone}: no first pass')
        ret = word(m.mem, z.sp)
        inside[0] = True
        m.run_to(ret, 10 * FRAME_T)
        inside[0] = False
    z.unmark_addrs(0xC000, 0x4000, z.WRITE_MARK)
    return m, seed, touched


def check(zones=range(125), out=print, png_dir=None, seeds=False, all_png=False):
    """Each zone in the harness against the model: [(zone, seed, bytes differing, bytes left out, map cells
    differing)]. seeds: a different seed poked for each zone (else the title's own, the same for all)."""
    results = []
    mem0 = initial_memory()
    n = ROWS * 8 * 64
    for zone in zones:
        m, seed, touched = harness_zone(zone, (zone * 40503 + 12345) & 0xFFFF if seeds else None)
        cpc = cpc_screen(m.mem)
        mz = build(bytearray(mem0), zone, seed)
        diff = [i for i in range(n) if not touched[i] and cpc[i] != mz.screen[i]]
        left = sum(touched[:n])
        maps = sum(1 for i in range(0x2C0) if mz.maps[i] != m.mem[0xB700 + i]) + \
            sum(1 for i in range(0x2C0) if mz.maps[0x300 + i] != m.mem[0xBA00 + i])
        results.append((zone, seed, len(diff), left, maps))
        out(f'zone {zone:3}: seed &{seed:04X}, {len(mz.placements):2} placements, {len(diff)} bytes differ, '
            f'{left} left out (sprites), {maps} map cells differ'
            + (f'; first at line {diff[0] // 64}, byte {diff[0] % 64}' if diff else ''))
        if png_dir and (diff or maps or all_png):
            os.makedirs(png_dir, exist_ok=True)
            inks = m.inks[:16]
            image(cpc, inks).save(os.path.join(png_dir, f'z{zone:03}_cpc.png'))
            image(mz.screen, inks).save(os.path.join(png_dir, f'z{zone:03}_model.png'))
        del m
    return results


if __name__ == '__main__':
    args = sys.argv[1:]
    if args and args[0] == '--check':
        zs = range(125)
        if len(args) > 1:
            a, _, b = args[1].partition('-')
            zs = range(int(a), int(b or a) + 1)
        res = check(zs, out=lambda s: print(s, flush=True), png_dir='work/zones/png', seeds='--seeds' in args,
                    all_png='--png' in args)
        print(f'{sum(1 for r in res if r[2] == 0 and r[4] == 0)} of {len(res)} zones match, screen and maps')
    else:
        zone = int(args[0]) if args else 0
        path = args[1] if len(args) > 1 and not args[1].startswith('--') else f'build/zone{zone}.png'
        seed = int(args[args.index('--seed') + 1], 0) if '--seed' in args else 0
        mem = initial_memory()
        z = build(mem, zone, seed)
        image(z.screen, [mem[INKS + i] for i in range(16)]).save(path)
        print(f'zone {zone}: {len(z.placements)} placements, {len(z.writes)} blocks, {len(z.stars)} stars -> {path}')
