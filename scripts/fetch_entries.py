import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Fetch selected entries from the remote SWDD zip via HTTP range requests."""
import os
import struct
import sys
import time
import urllib.request
import zlib

URL = "https://zenodo.org/api/records/10528135/files/SWDD%20-%20Dataset.zip/content"
ENTRIES = _os.path.join(REPO, "data", "swdd_entries.txt")
OUT_ROOT = _os.path.join(REPO, "data", "SWDD")
PREFIX = "SWDD - Dataset/Dataset/"


def load_entries():
    out = {}
    with open(ENTRIES, encoding="utf-8") as f:
        for line in f:
            name, method, csize, usize, lho = line.rstrip("\n").split("\t")
            out[name] = (int(method), int(csize), int(usize), int(lho))
    return out


def http_range(start, end, retries=8):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(URL)
            req.add_header("Range", "bytes=%d-%d" % (start, end))
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as e:  # noqa: BLE001
            last = e
            time.sleep(2 + attempt * 3)
    raise RuntimeError("range failed %d-%d: %r" % (start, end, last))


def fetch_entry(name, method, csize, usize, lho):
    if csize == 0:
        return None
    head = http_range(lho, lho + 29)
    if len(head) != 30 or head[:4] != b"PK\x03\x04":
        raise RuntimeError("bad local header for %s" % name)
    fnlen, extralen = struct.unpack("<HH", head[26:30])
    data_start = lho + 30 + fnlen + extralen
    raw = http_range(data_start, data_start + csize - 1)
    if len(raw) != csize:
        raise RuntimeError("short read for %s: %d/%d" % (name, len(raw), csize))
    if method == 0:
        return raw
    return zlib.decompress(raw, -15)


def main():
    entries = load_entries()
    wanted = [n for n in entries if n.startswith(PREFIX)]
    wanted.sort(key=lambda n: entries[n][3])
    if len(sys.argv) > 1 and sys.argv[1] == "annotations":
        wanted = [n for n in wanted if "/annotations/" in n]
    print("entries to fetch:", len(wanted), flush=True)
    total = 0
    for i, name in enumerate(wanted):
        method, csize, usize, lho = entries[name]
        rel = name[len(PREFIX):]
        if rel.endswith("/"):
            os.makedirs(os.path.join(OUT_ROOT, rel), exist_ok=True)
            continue
        dest = os.path.join(OUT_ROOT, rel)
        os.makedirs(os.path.dirname(dest), exist_ok=True)
        if os.path.exists(dest) and os.path.getsize(dest) == usize:
            total += csize
            continue
        data = fetch_entry(name, method, csize, usize, lho)
        with open(dest, "wb") as f:
            f.write(data)
        total += csize
        if (i + 1) % 20 == 0 or i + 1 == len(wanted):
            print("fetched %d/%d  (%.1f MB)" % (i + 1, len(wanted), total / 1e6), flush=True)
    print("complete", total / 1e6, "MB compressed", flush=True)


if __name__ == "__main__":
    main()
