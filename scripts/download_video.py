import os as _os
_here = _os.path.dirname(_os.path.abspath(__file__))
REPO = _os.path.dirname(_here) if _os.path.basename(_here) in ("tools", "scripts") else _here

# -*- coding: utf-8 -*-
"""Parallel resumable downloader for the SWDD video-frames byte range (2.2 GB)."""
import os
import queue
import threading
import time
import urllib.request

URL = "https://zenodo.org/api/records/10528135/files/SWDD%20-%20Dataset.zip/content"
START = 793528801
END = 2996794443
OUT = _os.path.join(REPO, "data", "video_slice.bin")
DONE = OUT + ".done"
TOTAL = END - START + 1
CHUNK = 4 * 1024 * 1024
WORKERS = 10

lock = threading.Lock()
completed = 0


def load_done():
    if not os.path.exists(DONE):
        return set()
    with open(DONE) as f:
        return {int(x) for x in f.read().split() if x.strip()}


def fetch(s, e, retries=8):
    last = None
    for attempt in range(retries):
        try:
            req = urllib.request.Request(URL)
            req.add_header("Range", "bytes=%d-%d" % (s, e))
            with urllib.request.urlopen(req, timeout=120) as r:
                data = r.read()
            if len(data) != e - s + 1:
                raise IOError("short %d/%d" % (len(data), e - s + 1))
            return data
        except Exception as exc:  # noqa: BLE001
            last = exc
            time.sleep(2 + attempt * 3)
    raise RuntimeError("chunk %d-%d failed: %r" % (s, e, last))


def worker(q, fd, done_set):
    global completed
    while True:
        try:
            idx = q.get_nowait()
        except queue.Empty:
            return
        if idx in done_set:
            q.task_done()
            continue
        s = START + idx * CHUNK
        e = min(s + CHUNK - 1, END)
        data = fetch(s, e)
        with lock:
            fd.seek(s - START)
            fd.write(data)
            fd.flush()
            with open(DONE, "a") as f:
                f.write("%d\n" % idx)
            done_set.add(idx)
            completed += 1
        q.task_done()


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    n_chunks = (TOTAL + CHUNK - 1) // CHUNK
    if not os.path.exists(OUT) or os.path.getsize(OUT) != TOTAL:
        with open(OUT, "wb") as f:
            f.truncate(TOTAL)
    done_set = load_done()
    print("chunks %d, done %d, total %.1f MB" % (n_chunks, len(done_set), TOTAL / 1e6), flush=True)
    q = queue.Queue()
    for i in range(n_chunks):
        q.put(i)
    fd = open(OUT, "r+b")
    t0 = time.time()
    threads = [threading.Thread(target=worker, args=(q, fd, done_set), daemon=True) for _ in range(WORKERS)]
    for t in threads:
        t.start()
    while any(t.is_alive() for t in threads):
        time.sleep(15)
        with lock:
            c, ds = completed, len(done_set)
        elapsed = max(time.time() - t0, 1e-6)
        print("%.1f%% (%d/%d) %.2f MB/s" % (ds * 100.0 / n_chunks, ds, n_chunks, c * CHUNK / elapsed / 1e6), flush=True)
    for t in threads:
        t.join()
    fd.close()
    print("final size", os.path.getsize(OUT), flush=True)


if __name__ == "__main__":
    main()
