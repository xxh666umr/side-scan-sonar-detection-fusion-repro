import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Extract the SWDD Dataset/ entries from the downloaded contiguous zip slice."""
import os
import struct
import sys
import zlib

BASE = 101551359
SLICE = _os.path.join(REPO, "data", "dataset_slice.bin")
ENTRIES = _os.path.join(REPO, "data", "swdd_entries.txt")
OUT_ROOT = _os.path.join(REPO, "data", "SWDD")
PREFIX = "SWDD - Dataset/Dataset/"


def main():
    entries = {}
    with open(ENTRIES, encoding="utf-8") as f:
        for line in f:
            name, method, csize, usize, lho = line.rstrip("\n").split("\t")
            entries[name] = (int(method), int(csize), int(usize), int(lho))

    names = [n for n in entries if n.startswith(PREFIX)]
    names.sort(key=lambda n: entries[n][3])

    with open(SLICE, "rb") as f:
        for i, name in enumerate(names):
            method, csize, usize, lho = entries[name]
            rel = name[len(PREFIX):]
            if rel == "" or rel.endswith("/"):
                os.makedirs(os.path.join(OUT_ROOT, rel), exist_ok=True)
                continue
            dest = os.path.join(OUT_ROOT, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            f.seek(lho - BASE)
            head = f.read(30)
            if head[:4] != b"PK\x03\x04":
                raise RuntimeError("bad local header at %s" % name)
            fnlen, extralen = struct.unpack("<HH", head[26:30])
            f.seek(lho - BASE + 30 + fnlen + extralen)
            raw = f.read(csize)
            if method == 0:
                data = raw
            else:
                data = zlib.decompress(raw, -15)
            if len(data) != usize:
                raise RuntimeError("size mismatch %s: %d != %d" % (name, len(data), usize))
            with open(dest, "wb") as out:
                out.write(data)
            if (i + 1) % 100 == 0:
                print("extracted %d/%d" % (i + 1, len(names)), flush=True)

    print("done", len(names), "entries", flush=True)


if __name__ == "__main__":
    main()
