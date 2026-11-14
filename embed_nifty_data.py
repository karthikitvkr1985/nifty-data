"""Embed the NIFTY50_*.csv files into Nifty_Algo_Backtester26.html.

Each CSV becomes a hidden <script type="application/octet-stream" id="nd-TF" data-n=ROWS> block
(zlib-compressed zigzag varints, base64) between the NIFTY-DATA markers; loadNifty() decodes it.
Run again after updating any CSV:  python3 embed_nifty_data.py
"""
import base64, os, re, zlib

ROOT = os.path.dirname(os.path.abspath(__file__))
HTML = os.path.join(ROOT, "Nifty_Algo_Backtester26.html")
FILES = [(1, "NIFTY50_1min.csv"), (3, "NIFTY50_3min.csv"), (5, "NIFTY50_5min.csv"),
         (15, "NIFTY50_15min.csv"), (60, "NIFTY50_1hour.csv"), (1440, "NIFTY50_daily.csv")]


def days(y, m, d):
    y -= m <= 2
    era = y // 400
    yoe = y - era * 400
    doy = (153 * (m + (-3 if m > 2 else 9)) + 2) // 5 + d - 1
    return era * 146097 + yoe * 365 + yoe // 4 - yoe // 100 + doy - 719468


def paise(s):
    return round(float(s) * 100)


def encode(path):
    rows = {}
    with open(path) as f:
        next(f)
        for ln in f:
            a = ln.strip().split(",")
            if len(a) < 5 or len(a[0]) < 16:
                continue
            d = a[0]
            # wall-clock time as in the CSV, like the app's own CSV loader
            m = days(int(d[:4]), int(d[5:7]), int(d[8:10])) * 1440 + int(d[11:13]) * 60 + int(d[14:16])
            rows[m] = (paise(a[1]), paise(a[2]), paise(a[3]), paise(a[4]))
    keys = sorted(rows)
    cols = [[], [], [], [], []]
    pm = pc = 0
    for m in keys:
        o, h, l, c = rows[m]
        cols[0].append(m - pm)
        cols[1].append(o - pc)
        cols[2].append(h - max(o, c))
        cols[3].append(min(o, c) - l)
        cols[4].append(c - o)
        pm, pc = m, c
    out = bytearray()
    for col in cols:
        for x in col:
            z = x * 2 if x >= 0 else -x * 2 - 1
            while z >= 128:
                out.append(z & 127 | 128)
                z >>= 7
            out.append(z)
    return len(keys), base64.b64encode(zlib.compress(bytes(out), 9)).decode()


def main():
    blocks = []
    for tf, name in FILES:
        n, b64 = encode(os.path.join(ROOT, name))
        lines = "\n".join(b64[i:i + 4096] for i in range(0, len(b64), 4096))
        blocks.append(f'<script type="application/octet-stream" id="nd-{tf}" data-n="{n}" data-src="{name}">\n{lines}\n</script>')
        print(f"{name}: {n} candles, {len(b64) / 1e6:.2f} MB")
    html = open(HTML, encoding="utf-8").read()
    pat = re.compile(r"<!--NIFTY-DATA-->.*?<!--/NIFTY-DATA-->", re.S)
    if not pat.search(html):
        raise SystemExit("NIFTY-DATA markers not found in " + HTML)
    html = pat.sub(lambda _: "<!--NIFTY-DATA-->\n" + "\n".join(blocks) + "\n<!--/NIFTY-DATA-->", html)
    open(HTML, "w", encoding="utf-8").write(html)
    print(f"{os.path.basename(HTML)}: {len(html) / 1e6:.2f} MB")


if __name__ == "__main__":
    main()
