"""The zones for the BBC (P8, D12, D21, D33): the object scripts and the placement lists as Baron source, and every
tile dithered to MODE 2, packed in small blocks so a zone change unpacks only what the zone needs.

    .venv/bin/python tools/genzones.py build/gen            # writes the files below
    .venv/bin/python tools/genzones.py build/gen --check    # and checks the BBC's form against zonemodel
    .venv/bin/python tools/genzones.py build/gen --expect   # and writes every zone's playfield as the BBC
                                                            # should draw it (zones-expected.bin), for
                                                            # tools/check_zones.mjs

- scripts.6502, raw in the code's bank: the script table (ZdScripts, a word an object) and the scripts. They keep
  the CPC's bytecodes (docs/cpc-zones.md) but for three changes: the Spectrum's attribute codes (&CF-&DE, &E0 n)
  are dropped, as they do nothing; &E3's operand is a label; and &E6's operand is one byte, the block set's
  number (1-21; 0 is the fixed tiles), not its CPC address.
- lists.6502: the placement lists (row, column, object; &FF ends) in five blocks, a stage of 25 zones each, each
  packed to unpack at ListBufOrg; ZdZones, each zone's list there; ZdStages, each stage's packed block.
- tilesets.6502: the fixed tiles raw (FixedTiles: global 0-8), each block set packed (TileSetLo/Hi), each set's
  first global tile (SetBaseLo/Hi). tiles.6502: the constants the code needs. tiles.bin: every tile, in order.

Global tile numbers (9 bits): 0 the blank (the font's space), 1-7 a star in pen 1-7, 8 the barrier, then the
21 block sets whole, in the order below (so the animations' blocks are in: the flames, the burning mine, the
guns' muzzles). A tile is 16 bytes in the screen's own order for a cell: the left byte's 8 lines, then the
right byte's. Each pixel is its pen's BBC colour, or its pair's by the pixel's place on the screen (x + y even:
the darker); a pixel of any pen but 0 has bit 3 set (logical 8-15: the palette makes them 0-7 again), so sprites
go behind it (P10, D31).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cpc import initial_memory, mode0_pens          # noqa: E402
from cpcdsk import read_dsk                         # noqa: E402
import gendata                                      # noqa: E402

ZONES, SCRIPTS = 0x490E, 0x1305
SETS = [(0x6F8D, 34), (0x71AD, 42), (0x744D, 20), (0x758D, 32), (0x778D, 20), (0x78CD, 20), (0x7A0D, 31),
        (0x7BFD, 42), (0x7E9D, 12), (0x7F5D, 8), (0x7FDD, 20), (0x811D, 25), (0x82AD, 18), (0x83CD, 29),
        (0x859D, 22), (0x8A1D, 3), (0x8A4D, 19), (0x8B7D, 29), (0x8D4D, 17), (0x8EDD, 21), (0x902D, 19)]
FONT, SPACE = 0x69DD, 0x20                          # the font's set and its space (the blank)
STAR, BARRIER = 0x302E, 0x38E5                      # the star's block (byte 8 set per star), the barrier's
FIRST_SET_GID = 9


def set_bases():
    bases, g = {}, FIRST_SET_GID
    for addr, n in SETS:
        bases[addr] = g
        g += n
    return bases, g


def w(m, a):
    return m[a] | m[a + 1] << 8


def parse(m, a):
    """A script from a: [(opcode, operands)] to its end byte, and the sub-scripts it calls."""
    out, subs = [], []
    while True:
        b = m[a]
        a += 1
        if b <= 0x60 or 0x90 <= b <= 0xCE or b in (0xE2, 0xE7, 0xE9, 0xEA):
            out.append((b, ()))
        elif b <= 0x8F or b in (0xE1, 0xE8, 0xEB):
            out.append((b, (m[a],)))
            a += 1
        elif b <= 0xDE:
            pass                                    # a Spectrum ink: dropped
        elif b == 0xE0:
            a += 1                                  # a Spectrum attribute: dropped
        elif b in (0xDF, 0xE4, 0xE5):
            out.append((b, (m[a], m[a + 1])))
            a += 2
        elif b in (0xE3, 0xE6):
            out.append((b, (w(m, a),)))
            if b == 0xE3:
                subs.append(w(m, a))
            a += 2
        else:
            out.append((0xFF, ()))
            return out, subs


def scripts(m):
    """Every object's script and every sub-script, parsed: {CPC address: ops}, and the object table."""
    table = [w(m, SCRIPTS + 2 * i) for i in range(62)]
    done, todo = {}, list(dict.fromkeys(table))
    while todo:
        a = todo.pop()
        if a in done:
            continue
        ops, subs = parse(m, a)
        done[a] = ops
        todo += subs
    return done, table


def zones(m):
    out = []
    for z in range(125):
        a, lst = w(m, ZONES + 2 * z), []
        while m[a] != 0xFF:
            lst.append(tuple(m[a:a + 3]))
            a += 3
        out.append(lst)
    return out


def label(a):
    return f'ZdS{a:04X}'


def set_index():
    return {addr: k + 1 for k, (addr, _) in enumerate(SETS)}


def emit_scripts(m, path):
    idx = set_index()
    done, table = scripts(m)
    lines = ['\\\\ scripts.6502 - made by tools/genzones.py from docs/exolon.dsk: the object scripts (P8), raw.', '',
             '.ZdScripts                              ; object n\'s script',
             '    EQUW ' + ', '.join(label(a) for a in table)]
    for a in sorted(done):
        bs = []
        for op, args in done[a]:
            if op == 0xE3:
                bs.append(f'&E3, LO({label(args[0])}), HI({label(args[0])})')
            elif op == 0xE6:
                bs.append(f'&E6, {idx[args[0]]}')
            else:
                bs.append(', '.join(f'&{x:02X}' for x in (op,) + args))
        assert sum(b.count(',') + 1 for b in bs) < 256, f'script &{a:04X}: 256 bytes or more'
        lines.append(f'.{label(a)}')
        for i in range(0, len(bs), 12):
            lines.append('    EQUB ' + ', '.join(bs[i:i + 12]))
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def emit_lists(m, path, stage=25):
    zs = zones(m)
    lines = ['\\\\ lists.6502 - made by tools/genzones.py from docs/exolon.dsk: the zones\' placement lists (P8, D33),',
             '\\\\ a block a stage, each packed to unpack at ListBufOrg.', '',
             '.ZdZones                                ; zone n\'s list, unpacked',
             '    EQUW ' + ', '.join(f'ZdZ{z}' for z in range(125)),
             '.ZdStages                               ; each stage\'s block, packed',
             '    EQUW ' + ', '.join(f'ZdStage{k}' for k in range((125 + stage - 1) // stage))]
    for k in range(0, 125, stage):
        lines += [f'.ZdStage{k // stage}', f'SECTION ZdStage{k // stage}Data, org = ListBufOrg, transform = "zx02"']
        for z in range(k, min(k + stage, 125)):
            lst = zs[z]
            lines.append(f'.ZdZ{z}')
            lines.append('    EQUB ' + ', '.join(f'{r}, {c}, {o}' for r, c, o in lst) + (', ' if lst else '') + '&FF')
        lines.append('ENDSECTION')
    with open(path, 'w') as f:
        f.write('\n'.join(lines) + '\n')


def emit_tilesets(tl, out):
    bases, n = set_bases()
    with open(os.path.join(out, 'fixedtiles.bin'), 'wb') as f:
        f.write(b''.join(tl[:FIRST_SET_GID]))
    lines = ['\\\\ tilesets.6502 - made by tools/genzones.py: the fixed tiles raw, each block set packed (D33).', '',
             '.FixedTiles                             ; global tiles 0-8: the blank, the stars, the barrier',
             '    INCBIN "fixedtiles.bin"',
             '.SetBaseLo                              ; each set\'s first global tile (set 0: the fixed tiles)',
             '    EQUB 0, ' + ', '.join(f'LO({bases[a]})' for a, _ in SETS),
             '.SetBaseHi',
             '    EQUB 0, ' + ', '.join(f'HI({bases[a]})' for a, _ in SETS),
             '.TileSetLo                              ; each set\'s packed block (set 0: none, the fixed tiles are raw)',
             '    EQUB 0, ' + ', '.join(f'LO(TileSet{k + 1})' for k in range(len(SETS))),
             '.TileSetHi',
             '    EQUB 0, ' + ', '.join(f'HI(TileSet{k + 1})' for k in range(len(SETS)))]
    for k, (a, size) in enumerate(SETS):
        g = bases[a]
        with open(os.path.join(out, f'tileset{k + 1}.bin'), 'wb') as f:
            f.write(b''.join(tl[g:g + size]))
        lines += [f'.TileSet{k + 1}', f'SECTION TileSet{k + 1}Data, org = TilesBufOrg, transform = "zx02"',
                  f'    INCBIN "tileset{k + 1}.bin"', 'ENDSECTION']
    with open(os.path.join(out, 'tilesets.6502'), 'w') as f:
        f.write('\n'.join(lines) + '\n')


def bbc_tile(cpc16, pairs, bit3=True):
    """A CPC block (16 bytes, row by row: left, right) to the BBC's: the left byte's 8 lines, the right's."""
    out = bytearray(16)
    for line in range(8):
        for side in range(2):
            left, right = mode0_pens(cpc16[2 * line + side])
            px = []
            for i, pen in enumerate((left, right)):
                x = 2 * side + i
                c = pairs[pen][(x + line) & 1]
                px.append(c | (8 if bit3 and pen else 0))
            out[side * 8 + line] = gendata.mode2_byte(px[0], px[1])
    return bytes(out)


def tiles(m, pairs):
    """Every tile by global number."""
    out = [bytes(16)]                               # 0: the blank
    star = bytearray(m[STAR:STAR + 16])
    for pen in range(1, 8):
        b = ((pen & 1) << 2) | ((pen & 2) << 3) | ((pen & 4) << 4)   # the right pixel's pen bits 0-2 (&54)
        star[8] = b
        out.append(bbc_tile(star, pairs))
    out.append(bbc_tile(m[BARRIER:BARRIER + 16], pairs))
    for addr, n in SETS:
        for k in range(n):
            out.append(bbc_tile(m[addr + 16 * k:addr + 16 * k + 16], pairs))
    return out


def check(m, pairs):
    """Run the BBC's form of every zone as the 6502 will (the rewritten scripts, global tile numbers) and compare
    each cell with zonemodel's (set, block): the same tile, by its BBC bytes."""
    import zonemodel
    bases, _ = set_bases()
    done, table = scripts(m)
    tl = tiles(m, pairs)
    zs = zones(m)
    bad = 0
    for z in range(125):
        ref = zonemodel.build(m, z, 0x6512)
        grid = [[None] * 32 for _ in range(22)]
        for (r, c) in [(r, c) for r in range(22) for c in range(32)]:
            t = ref.tiles[r][c]
            if t and t[0] == 'star':
                grid[r][c] = ('star', t[1])

        def run(a, d, e, base):
            ops = done[a]
            i, stack = 0, []
            while True:
                op, args = ops[i]
                i += 1
                if op <= 0x60:
                    if not (e & 0x20) and d < 22:
                        grid[d][e & 31] = base + op
                    e = (e + 1) & 255
                elif op <= 0x8F:
                    d = (d + op - 0x78) & 255
                    e = (e + args[0]) & 255
                elif op <= 0xCE:
                    d = (d + 1) & 255
                    e = (e + op - 0xAF) & 255
                elif op == 0xDF:
                    d, e = args
                elif op == 0xE1:
                    stack.append([i, args[0] or 256])
                elif op == 0xE2:
                    stack[-1][1] -= 1
                    if stack[-1][1]:
                        i = stack[-1][0]
                    else:
                        stack.pop()
                elif op == 0xE3:
                    base = run(args[0], d, e, base)
                elif op in (0xE4, 0xE5):
                    for _ in range(args[0] or 256):
                        if not (e & 0x20) and d < 22:
                            grid[d][e & 31] = base + args[1]
                        if op == 0xE4:
                            e = (e + 1) & 255
                        else:
                            d = (d + 1) & 255
                elif op == 0xE6:
                    base = bases[args[0]]
                elif op == 0xE7:
                    if not (e & 0x20) and d < 22:
                        grid[d][e & 31] = 0
                    e = (e + 1) & 255
                elif op == 0xFF:
                    return base
        for r, c, o in zs[z]:
            run(table[o], r, c, 0)
        for r in range(22):
            for c in range(32):
                t, g = ref.tiles[r][c], grid[r][c]
                if t is None or (t[0] != 'star' and t == (FONT, SPACE)):
                    want = bytes(16)
                elif t[0] == 'star':
                    want = None
                else:
                    s_, k = t
                    want = tl[8] if s_ == BARRIER else tl[bases[s_] + k] if s_ in bases else None
                got = (tl[g] if isinstance(g, int) else None)
                if t is not None and t[0] == 'star':
                    continue                        # (stars: drawn from the generator, checked on the BBC)
                if t is not None and t[0] == BARRIER:
                    continue                        # (the barrier: drawn by its own routine, not a script)
                if want is None or (got or bytes(16)) != want:
                    bad += 1
                    if bad < 10:
                        print(f'zone {z} cell ({r}, {c}): model {t}, BBC form {g}')
    print(f'{125 * 704 - bad} of {125 * 704} cells agree' if bad else 'every cell of all 125 zones agrees')
    return bad == 0


def expected(m, pairs, path, seed=0x6512):
    """Every zone's playfield as the BBC should draw it (rows 0-21, 11,264 bytes a zone, the screen's order): from
    zonemodel's tile map with the generator at seed, through the BBC's tiles."""
    import zonemodel
    bases, _ = set_bases()
    tl = tiles(m, pairs)
    out = bytearray()
    for z in range(125):
        ref = zonemodel.build(m, z, seed)
        for r in range(22):
            for c in range(32):
                t = ref.tiles[r][c]
                if t is None:
                    g = 0
                elif t[0] == 'star':
                    b = t[1]                        # the star block's byte 8: the pen's bits at &54
                    g = (b >> 2 & 1) | (b >> 3 & 2) | (b >> 4 & 4)
                elif t[0] == BARRIER:
                    g = 8
                elif t == (FONT, SPACE):
                    g = 0
                else:
                    g = bases[t[0]] + t[1]
                out += tl[g]
    with open(path, 'wb') as f:
        f.write(out)


def main(out, do_check=False):
    m = initial_memory()
    pairs = gendata.pairs(read_dsk(gendata.DSK))
    os.makedirs(out, exist_ok=True)
    emit_scripts(m, os.path.join(out, 'scripts.6502'))
    emit_lists(m, os.path.join(out, 'lists.6502'))
    tl = tiles(m, pairs)
    with open(os.path.join(out, 'tiles.bin'), 'wb') as f:
        f.write(b''.join(tl))
    emit_tilesets(tl, out)
    bases, n = set_bases()
    idx = set_index()
    with open(os.path.join(out, 'tiles.6502'), 'w') as f:
        f.write('\\\\ tiles.6502 - made by tools/genzones.py: the tiles\' and sets\' numbers the code needs\n\n'
                f'TileCount = {n}\nTileBlank = 0\nTileStar = 1                            ; 1-7: a star in pen 1-7\n'
                'TileBarrier = 8\n'
                f'TileFlames = {bases[0x6F8D] + 21}                         ; 6: the thruster flames\n'
                f'TileMine = {bases[0x6F8D] + 29}                           ; 4: the burning mine\n'
                f'TileMuzzles = {bases[0x758D] + 16}                        ; 16: the guns\' muzzles\n'
                f'SetCount = {len(SETS) + 1}                            ; the fixed tiles, then the 21 sets\n'
                f'SetFlames = {idx[0x6F8D]}                            ; the set the flames and the mine are in\n'
                f'SetMuzzles = {idx[0x758D]}                           ; and the muzzles\n')
    if '--expect' in sys.argv:
        expected(m, pairs, os.path.join(out, 'zones-expected.bin'))
    if do_check:
        sys.exit(0 if check(m, pairs) else 1)


if __name__ == '__main__':
    main(sys.argv[1] if len(sys.argv) > 1 else 'build/gen', '--check' in sys.argv)
