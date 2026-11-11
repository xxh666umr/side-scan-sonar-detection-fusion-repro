import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Extract video frames from the downloaded slice, with per-entry remote fallback."""
import os
import struct
import time
import urllib.request
import zlib

BASE = 793528801
SLICE = _os.path.join(REPO, "data", "video_slice.bin")
ENTRIES = _os.path.join(REPO, "data", "swdd_entries.txt")
OUT_ROOT = _os.path.join(REPO, "data", "SWDD_video")
PREFIX = "SWDD - Dataset/SSS-Video-frames/"
URL = "https://zenodo.org/api/records/10528135/files/SWDD%20-%20Dataset.zip/content"


def http_range(start, end, retries=8):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(URL)
            req.add_header("Range", "bytes=%d-%d" % (start, end))
            with urllib.request.urlopen(req, timeout=120) as r:
                return r.read()
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 + attempt * 3)
    raise RuntimeError("range failed %d-%d: %r" % (start, end, last))


def header_info(lho):
    head = http_range(lho, lho + 29)
    if head[:4] != b"PK\x03\x04":
        raise RuntimeError("bad remote local header")
    fnlen, extralen = struct.unpack("<HH", head[26:30])
    return lho + 30 + fnlen + extralen


def fetch_entry_remote(lho, method, csize):
    data_start = header_info(lho)
    raw = http_range(data_start, data_start + csize - 1)
    if len(raw) != csize:
        raise RuntimeError("short remote read")
    return raw if method == 0 else zlib.decompress(raw, -15)


def extract_from_slice(f, lho, method, csize, usize):
    f.seek(lho - BASE)
    head = f.read(30)
    if head[:4] != b"PK\x03\x04":
        raise RuntimeError("bad local header")
    fnlen, extralen = struct.unpack("<HH", head[26:30])
    f.seek(lho - BASE + 30 + fnlen + extralen)
    raw = f.read(csize)
    if len(raw) != csize:
        raise RuntimeError("short slice read")
    data = raw if method == 0 else zlib.decompress(raw, -15)
    if len(data) != usize:
        raise RuntimeError("size mismatch")
    return data


def main():
    entries = {}
    with open(ENTRIES, encoding="utf-8") as f:
        for line in f:
            name, method, csize, usize, lho = line.rstrip("\n").split("\t")
            entries[name] = (int(method), int(csize), int(usize), int(lho))
    names = [n for n in entries if n.startswith(PREFIX)]
    names.sort(key=lambda n: entries[n][3])
    print("entries:", len(names), flush=True)

    fallbacks = 0
    with open(SLICE, "rb") as f:
        for i, name in enumerate(names):
            method, csize, usize, lho = entries[name]
            rel = name[len(PREFIX):]
            if rel == "" or rel.endswith("/"):
                os.makedirs(os.path.join(OUT_ROOT, rel), exist_ok=True)
                continue
            dest = os.path.join(OUT_ROOT, rel)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            if os.path.exists(dest) and os.path.getsize(dest) == usize:
                continue
            try:
                data = extract_from_slice(f, lho, method, csize, usize)
            except Exception as exc:  # noqa: BLE001
                fallbacks += 1
                print("fallback %s (%s)" % (rel, str(exc)[:60]), flush=True)
                data = fetch_entry_remote(lho, method, csize)
                if len(data) != usize:
                    raise RuntimeError("still bad: %s" % name)
            with open(dest, "wb") as out:
                out.write(data)
            if (i + 1) % 1000 == 0:
                print("extracted %d/%d (fallback %d)" % (i + 1, len(names), fallbacks), flush=True)
    print("done, fallbacks:", fallbacks, flush=True)


if __name__ == "__main__":
    main()
