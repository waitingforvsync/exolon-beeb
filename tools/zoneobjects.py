"""The kinds of object each of Exolon's 125 zones holds, from the CPC data (docs/cpc-objects.md).

A zone's placements (row, column, object; table &490E) are run through the object scripts (table &1305,
interpreter &3CDD) as the zone set-up does (&12B4-&12E4), keeping the two cell maps: &B700 (0 where a
block hides sprites, &FF elsewhere) and &BA00 (1 where a block stops shots, 0 elsewhere, or a marker kind
2-17 from a script's &EB command). &1BE0 then turns each marker into a record of that kind's list, in
row-major order. Add the flying aliens (table &33A0, by zone), the destructible scenery (objects in the
table at &21DB) and the objects every zone has.

    .venv/bin/python tools/zoneobjects.py            # the table, one line a zone
    .venv/bin/python tools/zoneobjects.py --markdown # the same as a Markdown table
    .venv/bin/python tools/zoneobjects.py 17         # one zone's markers in detail

As a module: zone_objects(mem, zone) -> dict (see its docstring).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cpc import initial_memory                         # noqa: E402

ZONES = 0x490E          # 125 words: each zone's placements, (row, column, object) ... &FF
SCRIPTS = 0x1305        # 62 words: each object's script
BOXES = 0x21DB          # destructible objects: (object, x offset, width, y offset, height) ... &FF
ALIENS = 0x33A0         # flying aliens: (zone, path word, first frame, spawn gap) ... &FF

# The marker kinds (the value in &BA00; &1BE0's descriptor 6 * (kind - 2) at &1C4E).
KINDS = {
    2: ('lights', 0x1CE3, 5),
    3: ('gun', 0x1D7F, 4),
    4: ('unused', 0x1E5F, 0),
    5: ('mine', 0x1EDA, 10),
    6: ('teleport', 0x262A, 2),
    7: ('ammo', 0x26EC, 1),
    8: ('grenades', 0x26EF, 1),
    9: ('spores', 0x2855, 3),
    10: ('popup', 0x2975, 4),
    11: ('launcher', 0x2AC9, 10),
    12: ('exoskeleton', 0x2C71, 1),
    13: ('homing', 0x2F69, 1),
    14: ('bonus', 0x3063, 10),
    15: ('generator', 0x352A, 1),
    16: ('levelend', 0x3808, 1),
    17: ('barrier', 0x38E2, 1),
}


def word(mem, a):
    return mem[a] | mem[a + 1] << 8


def s8(b):
    return b - 256 if b & 0x80 else b


class Maps:
    """The cell maps as the zone set-up leaves them, and the blocks drawn."""

    def __init__(self):
        self.b700 = [0xFF] * 768
        self.ba00 = [0] * 768
        self.blocks = {}                                # (row, column) -> block number


def run_script(mem, maps, addr, d, e, state):
    """&3CDD: run the script at addr with the cursor at row d, column e. state holds &3BD5 and &3BCF."""
    def plot(a, d, e):
        if e & 0x20:                                    # &3B92: BIT 5,E / RET NZ
            return
        i = ((d & 0xFF) * 32 + (e & 0x1F)) & 0x3FF     # (the screen address halved, & &3FF)
        if i < 768:
            maps.b700[i] = state['b700']
            maps.ba00[i] = state['ba00']
            maps.blocks[(d & 0xFF, e & 0x1F)] = (state['base'], a)

    stack = []
    pc = addr
    while True:
        a = mem[pc]
        pc += 1
        if a < 0x61:
            plot(a, d, e)
            e = (e + 1) & 0xFF
        elif a < 0x90:
            d = (d + a - 0x78) & 0xFF
            e = (e + mem[pc]) & 0xFF
            pc += 1
        elif a < 0xCF:
            d = (d + 1) & 0xFF
            e = (e + a - 0xAF) & 0xFF
        elif a < 0xDF:
            pass                                        # a Spectrum attribute: nothing on the CPC
        elif a == 0xDF:
            d, e = mem[pc], mem[pc + 1]
            pc += 2
        elif a == 0xE0:
            pc += 1                                     # attribute
        elif a == 0xE1:
            stack.append((pc + 1, mem[pc]))
            pc += 1
        elif a == 0xE2:
            top, n = stack.pop()
            if n > 1:
                stack.append((top, n - 1))
                pc = top
        elif a == 0xE3:
            run_script(mem, maps, word(mem, pc), d, e, state)
            pc += 2
        elif a in (0xE4, 0xE5):
            n, b = mem[pc], mem[pc + 1]
            for _ in range(n or 256):
                plot(b, d, e)
                if a == 0xE4:
                    e = (e + 1) & 0xFF
                else:
                    d = (d + 1) & 0xFF
            pc += 2
        elif a == 0xE6:
            state['base'] = word(mem, pc)
            pc += 2
        elif a == 0xE7:
            plot(0x20, d, e)                            # (from &69DD; the base is put back after)
            e = (e + 1) & 0xFF
        elif a == 0xE8:
            state['ba00'] = mem[pc]
            pc += 1
        elif a == 0xE9:
            state['b700'] = 0
        elif a == 0xEA:
            state['b700'] = 0xFF
        elif a == 0xEB:
            i = (((d * 8) & 0xF8) >> 3) * 32 + (((e * 4) & 0x7C) >> 2)   # &2630 then &0ED8
            if i < 768:
                maps.ba00[i] = mem[pc]
            pc += 1
        else:
            return


def zone_objects(mem, zone):
    """A zone's objects: {'markers': {kind: [(column, row), ...]}, 'boxes': [(object, column, row)],
    'aliens': (path, frame, gap) or None, 'placements': [(row, column, object)], 'maps': Maps}."""
    maps = Maps()
    state = {'base': 0x69DD, 'ba00': 1, 'b700': 0}
    placements = []
    boxes = []
    boxobjs = {}
    a = BOXES
    while not mem[a] & 0x80:
        boxobjs[mem[a]] = a
        a += 5
    p = word(mem, ZONES + 2 * zone)
    while mem[p] != 0xFF:
        row, col, obj = mem[p], mem[p + 1], mem[p + 2]
        placements.append((row, col, obj))
        if obj in boxobjs:
            boxes.append((obj, col, row))
        state['ba00'], state['b700'] = 1, 0             # &12D5-&12DB
        run_script(mem, maps, word(mem, SCRIPTS + 2 * obj), row, col, state)
        p += 3
    markers = {}
    for i in range(0x2C0):                              # &1BE0 scans 22 rows
        v = maps.ba00[i]
        if v >= 2:
            markers.setdefault(v, []).append((i & 31, i >> 5))
    aliens = None
    a = ALIENS
    while mem[a] != 0xFF:
        if mem[a] == zone:
            aliens = (word(mem, a + 1), mem[a + 3], mem[a + 4])
            break
        a += 5
    return {'markers': markers, 'boxes': boxes, 'aliens': aliens, 'placements': placements, 'maps': maps}


def kinds_of(z):
    """The zone's kinds by name, in a fixed order."""
    out = [KINDS[k][0] for k in sorted(z['markers'])]
    if z['aliens']:
        out.append('aliens')
    if z['boxes']:
        out.append('scenery')
    return out


ALIEN_FRAMES = {}


def main():
    mem = initial_memory()
    args = sys.argv[1:]
    if args and args[0].isdigit():
        zone = int(args[0])
        z = zone_objects(mem, zone)
        print(f'zone {zone}: {len(z["placements"])} placements')
        for k, recs in sorted(z['markers'].items()):
            print(f'  kind {k:2} {KINDS[k][0]:12} ' + ' '.join(f'({c},{r})' for c, r in recs))
        print('  aliens', 'none' if not z['aliens'] else
              f'path &{z["aliens"][0]:04X} frames {z["aliens"][1]}-{z["aliens"][1] + 3} gap {z["aliens"][2]}')
        print('  destructible', ' '.join(f'obj {o} at ({c},{r})' for o, c, r in z['boxes']) or 'none')
        return
    md = '--markdown' in args
    if md:
        print('| Zone | Kinds (markers: count) | Aliens (path, frames, gap) | Destructible |')
        print('|---|---|---|---|')
    for zone in range(125):
        z = zone_objects(mem, zone)
        ks = ', '.join(f'{KINDS[k][0]}' + (f' {len(r)}' if len(r) > 1 else '')
                       for k, r in sorted(z['markers'].items()))
        al = (f'&{z["aliens"][0]:04X}, {z["aliens"][1]}-{z["aliens"][1] + 3}, {z["aliens"][2]}'
              if z['aliens'] else '')
        bx = len(z['boxes'])
        if md:
            print(f'| {zone} | {ks} | {al} | {bx or ""} |')
        else:
            print(f'{zone:3}: {ks:60} {al:20} {bx or ""}')


if __name__ == '__main__':
    main()
