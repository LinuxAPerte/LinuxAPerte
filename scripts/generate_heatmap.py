#!/usr/bin/env python3
"""
Genere contrib-heatmap.svg a partir des VRAIES contributions GitHub.
Cases qui s'allument une a une (pop + flash), style terminal.

Aucune authentification : on lit l'endpoint public de contributions.
Usage : python generate_heatmap.py [username] [sortie.svg]
Lance chaque jour par .github/workflows/update-profile-art.yml.
"""
import sys, json, datetime, urllib.request, re

USER = sys.argv[1] if len(sys.argv) > 1 else "LinuxAPerte"
OUT  = sys.argv[2] if len(sys.argv) > 2 else "contrib-heatmap.svg"

PALETTE = ["#161b22", "#0e4429", "#006d32", "#26a641", "#39d353"]
MONTHS  = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]


def _get(url):
    req = urllib.request.Request(url, headers={"User-Agent": "profile-readme-bot/1.0"})
    with urllib.request.urlopen(req, timeout=25) as r:
        return r.read().decode()


def fetch_days(user):
    """Retourne (days, total) ou days = [{'date','count','level'}...] tries."""
    # 1) API publique jogruber (rapide, donne deja les niveaux)
    try:
        data = json.loads(_get(f"https://github-contributions-api.jogruber.de/v4/{user}?y=last"))
        days = [{"date": c["date"], "count": c["count"], "level": int(c["level"])}
                for c in data["contributions"]]
        return days, data["total"]["lastYear"]
    except Exception as e:
        print(f"API jogruber KO ({e}), fallback HTML GitHub", file=sys.stderr)

    # 2) Fallback : page publique de contributions GitHub
    html = _get(f"https://github.com/users/{user}/contributions")
    days = []
    for m in re.finditer(r'data-date="(\d{4}-\d{2}-\d{2})"[^>]*data-level="(\d)"', html):
        days.append({"date": m.group(1), "count": None, "level": int(m.group(2))})
    days.sort(key=lambda d: d["date"])
    total = 0
    mt = re.search(r"([\d,]+)\s+contribution", html)
    if mt:
        total = int(mt.group(1).replace(",", ""))
    return days, total


def render(days, total):
    cell, step, x0, y0 = 13, 16, 34, 24
    start = datetime.date.fromisoformat(days[0]["date"])
    ncols = (len(days) + 6) // 7
    W = x0 + ncols * step + 6
    H = 158

    month_lbls, last_m = [], -1
    for wk in range(ncols):
        d = start + datetime.timedelta(days=wk * 7)
        if d.month != last_m:
            last_m = d.month
            month_lbls.append(f'<text class="lbl" x="{x0+wk*step}" y="16">{MONTHS[d.month-1]}</text>')
    day_lbls = ('<text class="lbl" x="2" y="51">Mon</text>'
                '<text class="lbl" x="2" y="83">Wed</text>'
                '<text class="lbl" x="2" y="115">Fri</text>')

    cells = []
    for i, c in enumerate(days):
        wk, row = i // 7, i % 7
        lvl = max(0, min(4, c["level"]))
        x, y = x0 + wk * step, y0 + row * step
        delay = wk * 0.065 + row * 0.0357
        cls = "c g" if lvl >= 1 else "c e"
        cells.append(f'<rect class="{cls}" x="{x}" y="{y}" width="{cell}" height="{cell}" '
                     f'rx="2.5" fill="{PALETTE[lvl]}" style="animation-delay:{delay:.3f}s"/>')

    return f'''<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="-apple-system,Segoe UI,Helvetica,Arial,sans-serif">
<style>
  text.lbl {{ fill:#7d8590; font-size:13px; font-weight:600; }}
  text.total {{ fill:#e6edf3; font-size:15px; font-weight:700; }}
  .c {{ transform-box:fill-box; transform-origin:center; opacity:0; animation:pop .55s ease-out both; }}
  .g {{ animation:pop .55s ease-out both, flash .7s ease-out both; }}
  @keyframes pop {{ 0%{{opacity:0;transform:scale(.2)}} 60%{{opacity:1;transform:scale(1.1)}} 100%{{opacity:1;transform:scale(1)}} }}
  @keyframes flash {{ 0%{{filter:brightness(2.4)}} 45%{{filter:brightness(2.4)}} 100%{{filter:brightness(1)}} }}
  @media (prefers-reduced-motion: reduce) {{ .c {{ opacity:1 !important; animation:none !important; }} }}
</style>
<rect width="{W}" height="{H}" fill="none"/>
{''.join(month_lbls)}{day_lbls}
{''.join(cells)}
<text class="total" x="34" y="152">{total:,} contributions in the last year</text>
</svg>'''


if __name__ == "__main__":
    days, total = fetch_days(USER)
    if not days:
        sys.exit("aucune donnee de contribution recuperee")
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(render(days, total))
    print(f"ecrit {OUT} : {len(days)} jours, {total} contributions")
