"""Map the CPC version's routines to the Spectrum original's, by matching their instruction streams with every
16-bit operand (addresses) masked, and list the 8-bit constants that differ between twins: where the game's
mechanics may differ between the two.

    .venv/bin/python tools/cpc2spec.py                     # every routine: CPC, Spectrum, constants that differ
    .venv/bin/python tools/cpc2spec.py 0FA2 1022           # just these (CPC addresses, hex)

The CPC image comes from tools/cpc.py's initial_memory(); the Spectrum's from tools/spectrum.py's snapshot
(build/spec/exolon.z80). Routine starts are the CPC trace's call targets and the main loop's callees. Twins
come two ways: the two main loops' calls paired in order (CPC &06C3-&0788, Spectrum &75BE-&7689); and a
masked signature (the first instructions, up to 24 bytes) found exactly once in the Spectrum's &6D60-&FFFF.
The twins are then compared instruction by instruction over the CPC routine's length (to the next routine's
start), until the code diverges.
"""
import difflib
import os
import re
import sys

sys.path.insert(0, os.path.dirname(__file__))
from cpc import initial_memory                          # noqa: E402
from z80trace import decode, trace                      # noqa: E402

SPEC_LO, SPEC_HI = 0x6D60, 0x10000


def operand16(m, a, n):
    """The offsets in an n-byte instruction at a that hold an address: a 16-bit operand, or a relative branch's
    displacement (both masked when matching: they move with the layout)."""
    op = m[a]
    if op in (0x10, 0x18, 0x20, 0x28, 0x30, 0x38):
        return (1,)
    if op in (0xDD, 0xFD):
        o2 = m[a + 1]
        return (2, 3) if n == 4 and o2 in (0x21, 0x22, 0x2A) else ()
    if op == 0xED:
        return (2, 3) if n == 4 else ()
    return (1, 2) if n == 3 else ()


def signature(m, a, limit=24):
    """A regex of the instructions from a: bytes literal, 16-bit operands any; and the instructions' starts."""
    parts, starts, length = [], [], 0
    while length < limit:
        n, kind, _ = decode(m, a + length)
        mask = operand16(m, a + length, n)
        parts.append(b''.join(b'.' if i in mask else re.escape(bytes([m[a + length + i]])) for i in range(n)))
        starts.append(length)
        length += n
        if kind in ('ret', 'jp', 'ind'):
            break
    return re.compile(b''.join(parts), re.S), length


def routines(m):
    _, calls, _ = trace(m, [0x0100], 0x0100, 0xB1CD)
    loop = [m[a + 1] | m[a + 2] << 8 for a in range(0x06C3, 0x0788) if m[a] == 0xCD]
    return sorted(set(calls) | set(loop))


def loop_pairs(c, s):
    """The two main loops' calls (CALL and CALL cc), paired in order: {cpc: spec}."""
    def calls(m, lo, hi):
        out, a = [], lo
        while a < hi:
            n, kind, t = decode(m, a)
            if kind == 'call' and t is not None:
                out.append(t)
            a += n
        return out
    def key(m, t):                                      # the callee's first bytes, addresses zeroed
        out, off = bytearray(), 0
        while off < 12:
            n, _, _ = decode(m, t + off)
            mask = operand16(m, t + off, n)
            out += bytes(0 if i in mask else m[t + off + i] for i in range(n))
            off += n
        return bytes(out)
    cl, sl = calls(c, 0x06C3, 0x0788), calls(s, 0x75BE, 0x7689)
    sm = difflib.SequenceMatcher(None, [key(c, t) for t in cl], [key(s, t) for t in sl], autojunk=False)
    return {cl[i + k]: sl[j + k] for i, j, n in sm.get_matching_blocks() for k in range(n)}


def compare(c, s, ca, sa, limit=400):
    """Walk the twins together: [(cpc addr, spec addr, what differs)] for differing 8-bit constants."""
    diffs, off = [], 0
    while off < limit:
        n, kind, _ = decode(c, ca + off)
        n2, _, _ = decode(s, sa + off)
        if n != n2 or c[ca + off] != s[sa + off]:
            diffs.append((ca + off, sa + off, 'the code diverges here'))
            break
        mask = operand16(c, ca + off, n)
        for i in range(1, n):
            if i not in mask and c[ca + off + i] != s[sa + off + i]:
                diffs.append((ca + off, sa + off, f'byte +{i}: CPC &{c[ca + off + i]:02X}, Spectrum &{s[sa + off + i]:02X}'))
        off += n
    return diffs


def main(only=None):
    from spectrum import Spectrum
    c = initial_memory()
    s = bytes(Spectrum().mem)
    spec = s[SPEC_LO:SPEC_HI]
    found = missing = 0
    pairs = loop_pairs(c, s)
    starts = routines(c)
    for a in (only or starts):
        sig, length = signature(c, a)
        hits = [pairs[a]] if a in pairs else [SPEC_LO + x.start() for x in sig.finditer(spec)]
        if len(hits) != 1:
            missing += 1
            print(f'CPC &{a:04X}: {"no twin" if not hits else str(len(hits)) + " candidates"} ({length} bytes signed)')
            continue
        found += 1
        end = min([b for b in starts if b > a] + [0xB1CD])
        diffs = compare(c, s, a, hits[0], end - a)
        print(f'CPC &{a:04X} = Spectrum &{hits[0]:04X}' + ('' if not diffs else ': ' + '; '.join(
            f'&{ca:04X}/&{sa:04X} {d}' for ca, sa, d in diffs)))
    if not only:
        print(f'{found} routines with one twin, {missing} without')


if __name__ == '__main__':
    main([int(x, 16) for x in sys.argv[1:]] or None)
