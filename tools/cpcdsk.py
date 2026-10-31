"""Read the files from a CPCEMU DSK in data format (sectors &C1-&C9, 1K blocks, the directory in blocks 0-1).

    from cpcdsk import read_dsk
    files = read_dsk('docs/exolon.dsk')     # {'EXOLON.1': {'data', 'load', 'exec', 'length'}, ...}

'data' is the file's body without its AMSDOS header; files with no header keep all their records.
Run as a script, it lists the disc.
"""
import struct
import sys


def read_dsk(path):
    d = open(path, 'rb').read()
    assert d[:8] == b'MV - CPC', 'not a standard DSK'
    tracks, tsize = d[0x30], struct.unpack('<H', d[0x32:0x34])[0]
    sectors = {}
    for t in range(tracks):
        base = 0x100 + t * tsize
        info = d[base:base + 0x100]
        assert info[:10] == b'Track-Info', f'track {t}'
        off = base + 0x100
        for s in range(info[0x15]):
            size = 128 << info[0x18 + 8 * s + 3]
            sectors[(t, info[0x18 + 8 * s + 2])] = d[off:off + size]
            off += size

    def block(b):
        return b''.join(sectors[divmod(n, 9)[0], 0xC1 + divmod(n, 9)[1]] for n in (2 * b, 2 * b + 1))

    directory = block(0) + block(1)
    extents = {}
    for i in range(64):
        e = directory[32 * i:32 * i + 32]
        if e[0] == 0xE5:
            continue
        name = bytes(c & 0x7F for c in e[1:9]).decode().rstrip()
        ext = bytes(c & 0x7F for c in e[9:12]).decode().rstrip()
        extents.setdefault(f'{name}.{ext}' if ext else name, []).append((e[12], e[15], [b for b in e[16:32] if b]))
    files = {}
    for name, exts in extents.items():
        raw = b''.join(b''.join(block(b) for b in blocks)[:rc * 128] for _, rc, blocks in sorted(exts))
        h = raw[:128]
        check = sum(h[:67]) & 0xFFFF
        if check and check == struct.unpack('<H', h[67:69])[0]:
            length = struct.unpack('<H', h[0x18:0x1A])[0]
            files[name] = {'data': raw[128:128 + length], 'load': struct.unpack('<H', h[0x15:0x17])[0],
                           'exec': struct.unpack('<H', h[0x1A:0x1C])[0], 'length': length}
        else:
            files[name] = {'data': raw, 'load': None, 'exec': None, 'length': len(raw)}
    return files


if __name__ == '__main__':
    for name, f in sorted(read_dsk(sys.argv[1] if len(sys.argv) > 1 else 'docs/exolon.dsk').items()):
        if f['load'] is None:
            print(f'{name:12} {f["length"]:6} bytes, no header')
        else:
            print(f'{name:12} {f["length"]:6} bytes, load &{f["load"]:04X}, exec &{f["exec"]:04X}')
