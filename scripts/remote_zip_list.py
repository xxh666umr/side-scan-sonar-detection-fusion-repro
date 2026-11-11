import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""List entries of a remote ZIP via HTTP range requests (no full download)."""
import struct
import urllib.request

URL = "https://zenodo.org/api/records/10528135/files/SWDD%20-%20Dataset.zip/content"
TOTAL = 2998738985


def fetch_range(start, end):
    req = urllib.request.Request(URL)
    req.add_header("Range", "bytes=%d-%d" % (start, end))
    with urllib.request.urlopen(req, timeout=180) as r:
        return r.read()


def main():
    tail_start = max(0, TOTAL - 100000)
    tail = fetch_range(tail_start, TOTAL - 1)
    idx = tail.rfind(b"PK\x05\x06")
    if idx < 0:
        raise SystemExit("EOCD not found")
    eocd = tail[idx:idx + 22]
    (sig, disk, cd_disk, n_disk, n_total, cd_size, cd_off, comment_len) = struct.unpack("<4sHHHHIIH", eocd)
    print("entries:", n_total, "cd_size:", cd_size, "cd_offset:", cd_off, flush=True)

    data = b""
    pos = cd_off
    end = cd_off + cd_size - 1
    while pos <= end:
        chunk_end = min(pos + 8 * 1024 * 1024 - 1, end)
        data += fetch_range(pos, chunk_end)
        pos = chunk_end + 1
    print("cd bytes:", len(data), flush=True)

    entries = []
    p = 0
    while p + 46 <= len(data):
        if data[p:p + 4] != b"PK\x01\x02":
            break
        (sig, ver_made, ver_need, flags, method, mtime, mdate, crc, csize, usize,
         fnlen, extralen, commentlen, disk_start, iattr, eattr, lho) = struct.unpack(
            "<4sHHHHHHIIIHHHHHII", data[p:p + 46])
        name = data[p + 46:p + 46 + fnlen].decode("utf-8", "replace")
        entries.append((name, method, csize, usize, lho))
        p += 46 + fnlen + extralen + commentlen

    total = sum(e[3] for e in entries)
    print("parsed entries:", len(entries), "uncompressed total %.2f GB" % (total / 1e9), flush=True)

    from collections import defaultdict
    groups = defaultdict(lambda: [0, 0, 0])
    for name, method, csize, usize, lho in entries:
        parts = name.split("/")
        key = "/".join(parts[:2]) if len(parts) > 1 else parts[0]
        if parts[-1] == "":
            key = name
        g = groups[key]
        g[0] += 1
        g[1] += csize
        g[2] += usize
    print("\n%-70s %8s %12s %12s" % ("group", "files", "compressed", "uncompressed"))
    for key in sorted(groups):
        c, cs, us = groups[key]
        print("%-70s %8d %12.1f %12.1f" % (key[:70], c, cs / 1e6, us / 1e6))

    with open(_os.path.join(REPO, "data", "swdd_entries.txt"), "w", encoding="utf-8") as f:
        for name, method, csize, usize, lho in entries:
            f.write("%s\t%d\t%d\t%d\t%d\n" % (name, method, csize, usize, lho))
    print("\nsaved entry list", flush=True)


if __name__ == "__main__":
    main()
