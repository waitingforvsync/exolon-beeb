"""The BBC's game against the CPC original in lockstep: the same keys into both, pass by pass, and their state
compared (docs/plan.md's Phase 3 check).

    .venv/bin/python tools/lockstep.py --passes 300 --keys random:1 [--zone 0]

The CPC runs in tools/cpc.py from the title (its seed then the BBC's TitleSeed); the BBC in headless jsbeeb
(tools/lockstep.mjs). Each pass's state is a few named variables, the CPC's address against the BBC's symbol.
Prints the first passes that differ.
"""
import argparse
import os
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.dirname(__file__))
import plotlog                                      # noqa: E402

# name: (the CPC's address, the BBC's symbol)
STATE = {'x': (0x10EE, 'PlX'), 'y': (0x10EF, 'PlY'), 'jump': (0x10F0, 'PlJump'), 'frame': (0x1062, 'PlFrame'),
         'fell': (0x108D, 'PlFell'), 'dir': (0x10F1, 'PlDir')}
BITS = {'o': 1, 'p': 2, 'q': 4, 'a': 8, 'space': 16}       # the CPC's keys as GameKeys' bits (Z X : / RETURN)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--passes', type=int, default=300)
    ap.add_argument('--keys', default='random:1')
    ap.add_argument('--state', default=','.join(STATE))
    ap.add_argument('--zone', type=int, default=None)
    ap.add_argument('--nofire', action='store_true', help='fire never held (for what the BBC lacks yet)')
    ap.add_argument('--invulnerable', action='store_true', help='the CPC never dies (for what the BBC lacks yet)')
    a = ap.parse_args()
    names = a.state.split(',')
    keys = plotlog.random_keys(int(a.keys.split(':')[1])) if a.keys.startswith('random:') else (lambda i: set(a.keys.split()))
    seq = [keys(i) - ({'space'} if a.nofire else set()) for i in range(a.passes)]
    m = plotlog.start(zone=a.zone, invulnerable=a.invulnerable)
    cpc = []
    for i, k in enumerate(seq):
        m.run_passes(1, lambda _: k)
        cpc.append([m.mem[STATE[n][0]] for n in names])
    with tempfile.NamedTemporaryFile('w', suffix='.keys', delete=False) as f:
        f.write('\n'.join(str(sum(BITS[c] for c in k)) for k in seq) + '\n')
        kfile = f.name
    root = os.path.join(os.path.dirname(__file__), '..')
    out = subprocess.run(['node', 'tools/lockstep.mjs', '--keys', kfile, '--vars', ','.join(STATE[n][1] for n in names)],
                         cwd=root, capture_output=True, text=True, check=True).stdout
    os.unlink(kfile)
    bbc = [[int(v) for v in line.split()] for line in out.strip().split('\n') if line and line[0].isdigit()]
    bad = 0
    for i, (c, b) in enumerate(zip(cpc, bbc)):
        if c != b:
            bad += 1
            if bad <= 10:
                print(f'pass {i} keys {sorted(seq[i])}: CPC ' + ' '.join(f'{n} {v}' for n, v in zip(names, c)) +
                      ' | BBC ' + ' '.join(f'{n} {v}' for n, v in zip(names, b)))
    print(f'{len(bbc)} passes compared, {bad} differ ({", ".join(names)})')


if __name__ == '__main__':
    main()
