"""A SkoolKit control file for the CPC image, from a recursive-descent trace: code where the trace reached,
bytes elsewhere. The start for the disassembly the specs (docs/cpc-*.md) are written from.

    .venv/bin/python tools/mkctl.py build/exolon.ctl build/exolon64k.bin
    .venv/bin/sna2skool.py -H -o 0 -c build/exolon.ctl build/exolon64k.bin > build/exolon.skool

Entry points beyond &0100: the sound's dispatch table at &64A8 (the computed JP (HL) at &64A7).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cpc import initial_memory                          # noqa: E402
from z80trace import trace                              # noqa: E402

START, END = 0x0100, 0xB1CD                             # the game's image, as the loader leaves it


def entries(m):
    w = lambda a: m[a] | m[a + 1] << 8                  # noqa: E731
    return [0x0100] + sorted({w(0x64A8 + 2 * i) for i in range(16)})


def main(ctl, binary):
    m = initial_memory()
    with open(binary, 'wb') as f:
        f.write(m)
    code, calls, _ = trace(m, entries(m), START, END)
    lines = [f'@ ${START:04X} start', f'@ ${START:04X} org']
    kind = None
    for a in range(START, END):
        k = 'c' if code[a] else 'b'
        if k != kind or (k == 'c' and a in calls):
            lines.append(f'{k} ${a:04X}')
            kind = k
    lines.append(f'i ${END:04X}')
    with open(ctl, 'w') as f:
        f.write('\n'.join(lines) + '\n')


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
