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


def objects(log):
    """The passes as objects, for src/plotpass.6502's plot_pass (bench.6502's commands 10-14): each large sprite
    plotted (its last plot in the pass) or gone, and each 8-line sprite moved (an erase and the draw PAIRS8
    pairs it with), put on or taken off: each image the pass XORs off if it's on the screen before the pass,
    on if it is after. The blank frame (6) is left out."""
    slots, out, shown = {}, [], Counter()
    for plots in log:
        if any(p.kind == 'clear' for p in plots):
            break
        large, smalls, pend = {}, [], {}
        for p in plots:
            if p.pad:
                continue
            if p.kind in ('player', 'obj16'):
                slot = slots.setdefault(p.save, len(slots))
                assert slot < 16, 'more large sprites than slots'
                large[slot] = (10, slot, sprite(p), p.x, p.y) if p.draw else (11, slot)
            elif p.kind == 'obj8' and p.frame != 6:
                img = (sprite(p), p.x, p.y)
                if p.erase:
                    rec = [img, None]
                    smalls.append(rec)
                    if p.caller in plotlog.PAIRS8:
                        pend[plotlog.PAIRS8[p.caller]] = rec
                elif p.caller in pend:
                    pend.pop(p.caller)[1] = img
                else:
                    smalls.append([None, img])
        # each image the pass XORs: taken off if it's on the screen before the pass, put on if it is after (an
        # odd number of XORs changing which), so every off is of an image there, every image there at a store
        # is known, and none is XORed twice in one phase (plot_pass XORs a region's offs before its ons); a
        # record's off and on stay paired where both are kept
        toggles = Counter()
        for off, on in smalls:
            for img in (off, on):
                if img:
                    toggles[img] += 1
        before = {img: shown[img] for img in toggles}
        after = {img: before[img] ^ (toggles[img] & 1) for img in toggles}
        offs_done, ons_done, recs = set(), set(), []
        for off, on in smalls:
            o = off if off and before[off] and off not in offs_done else None
            n = on if on and after[on] and on not in ons_done else None
            if o:
                offs_done.add(o)
            if n:
                ons_done.add(n)
            if o or n:
                recs.append([o, n])
        for img in toggles:                         # (an image's off or on left: its own record)
            if before[img] and img not in offs_done:
                recs.append([img, None])
            if after[img] and img not in ons_done:
                recs.append([None, img])
        for img in toggles:
            shown[img] = after[img]
        cmds = list(large.values())
        for off, on in recs:
            if off and on:
                cmds.append((12,) + off + on)
            elif on:
                cmds.append((13,) + on)
            elif off:
                cmds.append((14,) + off)
        c = bytes(b for cmd in cmds for b in cmd) + b'\0'
        assert len(c) <= 1024, 'a pass longer than CmdBuf'
        out.append(c)
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--zone', type=int, default=0)
    ap.add_argument('--passes', type=int, default=400)
    ap.add_argument('--keys', default='random:1')
    ap.add_argument('--objects', action='store_true', help="the passes as objects (plot_pass's)")
    a = ap.parse_args()
    keys = plotlog.random_keys(int(a.keys.split(':')[1])) if a.keys.startswith('random:') else (lambda i: set(a.keys.split()))
    log = plotlog.run(zone=a.zone, passes=a.passes, keys=keys)
    if a.objects:
        passes, twice, unshown = objects(log), 0, 0
    else:
        passes, twice, unshown = commands(log)
    os.makedirs(os.path.dirname(a.out) or '.', exist_ok=True)
    with open(a.out, 'wb') as f:
        for c in passes:
            f.write(struct.pack('<H', len(c)) + c)
    print(f'{len(passes)} passes, {sum(len(c) for c in passes)} bytes of commands, the longest {max(map(len, passes))}; '
          f'{twice} large plots dropped for a later one in their pass, {unshown} XORs off of 8-line images not shown')


if __name__ == '__main__':
    main()
