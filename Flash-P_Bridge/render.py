"""Render FLASH-P analysis results as a branded PNG card + a full styled HTML report.

Reads the TSVs the drivers already write (`gxe/gxe_anchored.tsv`,
`epistasis/epistasis_doubles.tsv`) and produces, in the analysis output dir:
  - `<analysis>_card.png`   — an inline result card in the FLASH-P theme (Pillow)
  - `<analysis>_report.html`— the full report, all tables, FLASH-P theme (HTML/CSS)

Brand palette + fonts come from FLASHP_WEBSITE/Flash-P-AI. Everything renders offline
(Pillow + bundled fonts in assets/; the HTML only pulls Google Fonts when opened).
"""
from __future__ import annotations

import csv
import html
from collections import Counter
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ASSETS = Path(__file__).resolve().parent / "assets"

# ---- FLASH-P palette (hex) -------------------------------------------------
PRIMARY = "#E67E22"          # brand orange
PRIMARY_DK = "#C75E12"
GOLD = "#D4A76A"
TEAL = "#2D7D5F"
BG = "#FEFBF7"               # warm off-white
CARD = "#FFFFFF"
TEXT = "#1A1410"             # dark brown
MUTED = "#8A7E74"
BORDER = "#E7DFD7"
BAND = "#FAF3EA"             # subtle row band
POS = "#0E9F6E"             # activation / positive
NEG = "#D8341C"             # inhibition / negative
CLASS_COLORS = {
    "synergy": "#D8341C", "buffering": "#2F73C7", "reshaping": "#7C4DD6",
    "masking": "#9A8E84", "additive": "#BCB3AA", "undefined": "#9A8E84",
}


def _font(name: str, size: int, weight: int = 400):
    try:
        f = ImageFont.truetype(str(ASSETS / name), size)
        try:
            f.set_variation_by_axes([weight])   # variable-font weight
        except Exception:
            pass
        return f
    except Exception:
        return ImageFont.load_default()


def _hx(c: str):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


# ---- data parsing ----------------------------------------------------------
def _read_tsv(path: Path) -> list[dict]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8") as f:
        return list(csv.DictReader(f, delimiter="\t"))


def _f(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def _truthy(v) -> bool:
    return str(v).strip().lower() in ("true", "1", "yes")


def _gxe_data(net_dir: Path) -> dict:
    rows = _read_tsv(net_dir / "gxe" / "gxe_anchored.tsv")
    hits = sorted(rows, key=lambda r: abs(_f(r.get("gxe_alg"))), reverse=True)
    sig = [r for r in rows if _truthy(r.get("gxe_significant_alg"))]
    agree = [r for r in sig if (_f(r.get("gxe_alg")) >= 0) == (_f(r.get("gxe_ode")) >= 0)]
    doses = sorted({r.get("env_value") for r in rows if r.get("env_value")})
    envs = sorted({r.get("env") for r in rows if r.get("env")})
    return {
        "rows": rows, "hits": hits, "n_sig": len(sig), "envs": envs, "doses": doses,
        "agreement": (len(agree) / len(sig)) if sig else None,
    }


def _epi_data(net_dir: Path) -> dict:
    rows = _read_tsv(net_dir / "epistasis" / "epistasis_doubles.tsv")
    classes = Counter(r.get("interaction_class", "additive") for r in rows)
    genuine = [r for r in rows if r.get("interaction_class") in ("buffering", "synergy", "reshaping")]
    genuine.sort(key=lambda r: abs(_f(r.get("epistasis_algebraic"))), reverse=True)
    return {"rows": rows, "classes": classes, "genuine": genuine, "n_pairs": len(rows)}


# ---- PNG card --------------------------------------------------------------
def _draw_table(draw, x, y, width, columns, rows, fonts, row_accent=None):
    """columns: list of (header, frac, align). rows: list of (cells, cell_colors)."""
    hdr_f, cell_f = fonts["thead"], fonts["cell"]
    xs, acc = [], 0
    for _, frac, _a in columns:
        xs.append(x + int(acc * width)); acc += frac
    xs.append(x + width)
    rh = 46
    # header
    draw.rectangle([x, y, x + width, y + 40], fill=_hx(BAND))
    for i, (h, _f_, align) in enumerate(columns):
        draw.text((xs[i] + 12, y + 10), h, font=hdr_f, fill=_hx(MUTED))
    y += 44
    for ri, (cells, colors) in enumerate(rows):
        if ri % 2 == 1:
            draw.rectangle([x, y, x + width, y + rh], fill=_hx(BAND))
        if row_accent and ri < len(row_accent) and row_accent[ri]:
            draw.rectangle([x, y, x + 5, y + rh], fill=_hx(row_accent[ri]))
        for i, (h, _f_, align) in enumerate(columns):
            txt = str(cells[i])
            col = _hx(colors[i]) if colors and colors[i] else _hx(TEXT)
            tx = xs[i] + 12
            if align == "r":
                w = draw.textlength(txt, font=cell_f)
                tx = xs[i + 1] - 12 - w
            draw.text((tx, y + 12), txt, font=cell_f, fill=col)
        draw.line([x, y + rh, x + width, y + rh], fill=_hx(BORDER), width=1)
        y += rh
    return y


def _render_png(out: Path, kicker: str, title: str, columns, rows, row_accent, footer: str):
    W, M = 1040, 40
    head_h = 96
    body_top = head_h + 28
    height = body_top + 70 + 44 + len(rows) * 46 + 70
    img = Image.new("RGB", (W, height), _hx(BG))
    d = ImageDraw.Draw(img)
    fonts = {
        "wordmark": _font("SpaceGrotesk.ttf", 38, 700),
        "kicker": _font("JetBrainsMono.ttf", 19, 500),
        "title": _font("SpaceGrotesk.ttf", 30, 600),
        "thead": _font("JetBrainsMono.ttf", 18, 600),
        "cell": _font("JetBrainsMono.ttf", 19, 500),
        "foot": _font("JetBrainsMono.ttf", 16, 400),
    }
    # header band (orange)
    d.rectangle([0, 0, W, head_h], fill=_hx(PRIMARY))
    d.ellipse([M, head_h // 2 - 13, M + 26, head_h // 2 + 13], fill=_hx(BG))
    d.text((M + 40, head_h // 2 - 22), "FLASH-P", font=fonts["wordmark"], fill=_hx(BG))
    kw = d.textlength(kicker, font=fonts["kicker"])
    d.text((W - M - kw, head_h // 2 - 11), kicker, font=fonts["kicker"], fill=_hx(BG))
    # title
    d.text((M, body_top), title, font=fonts["title"], fill=_hx(TEXT))
    # table
    y = _draw_table(d, M, body_top + 52, W - 2 * M, columns, rows, fonts, row_accent)
    # footer — truncate the left text so it never collides with the brand on the right
    d.line([M, y + 16, W - M, y + 16], fill=_hx(BORDER), width=1)
    brand = "flash-p.com"
    brand_w = d.textlength(brand, font=fonts["foot"])
    avail = (W - M - brand_w - 24) - M
    foot = footer
    if d.textlength(foot, font=fonts["foot"]) > avail:
        while foot and d.textlength(foot + "…", font=fonts["foot"]) > avail:
            foot = foot[:-1]
        foot = foot.rstrip(" ·") + "…"
    d.text((M, y + 30), foot, font=fonts["foot"], fill=_hx(MUTED))
    d.text((W - M - brand_w, y + 30), brand, font=fonts["foot"], fill=_hx(PRIMARY))
    img.save(out)
    return out


# ---- HTML report -----------------------------------------------------------
_CSS = f"""
@import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap');
:root{{--p:{PRIMARY};--bg:{BG};--text:{TEXT};--muted:{MUTED};--border:{BORDER};--band:{BAND};}}
*{{box-sizing:border-box}}
body{{margin:0;background:var(--bg);color:var(--text);font-family:'Space Grotesk',sans-serif;}}
.head{{background:linear-gradient(135deg,{PRIMARY},{GOLD},{TEAL});color:#fff;padding:28px 32px;}}
.head h1{{margin:0;font-size:26px;letter-spacing:.5px}}
.head .sub{{font-family:'JetBrains Mono',monospace;opacity:.92;margin-top:4px;font-size:14px}}
.wrap{{max-width:980px;margin:0 auto;padding:24px 32px 60px}}
h2{{font-size:18px;margin:30px 0 10px;color:var(--p)}}
table{{width:100%;border-collapse:collapse;font-family:'JetBrains Mono',monospace;font-size:13.5px}}
th{{text-align:left;color:var(--muted);font-weight:600;border-bottom:2px solid var(--border);padding:8px 10px}}
td{{padding:7px 10px;border-bottom:1px solid var(--border)}}
tr:nth-child(even) td{{background:var(--band)}}
.pos{{color:{POS};font-weight:600}} .neg{{color:{NEG};font-weight:600}}
.pill{{display:inline-block;padding:2px 10px;border-radius:10px;color:#fff;font-size:12px;font-weight:600}}
.foot{{margin-top:34px;color:var(--muted);font-family:'JetBrains Mono',monospace;font-size:12px}}
.foot a{{color:var(--p);text-decoration:none}}
"""


def _html_table(headers, rows_html) -> str:
    head = "".join(f"<th>{html.escape(h)}</th>" for h in headers)
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(rows_html)}</tbody></table>"


def _num(v, signed=True):
    x = _f(v)
    cls = "pos" if x >= 0 else "neg"
    return f'<span class="{cls}">{x:+.2f}</span>' if signed else f"{x:.2f}"


def _render_html(out: Path, subtitle: str, sections: list[str], footer: str):
    body = "".join(sections)
    out.write_text(
        f"<!doctype html><html><head><meta charset='utf-8'>"
        f"<meta name='viewport' content='width=device-width,initial-scale=1'>"
        f"<title>FLASH-P · {html.escape(subtitle)}</title><style>{_CSS}</style></head><body>"
        f"<div class='head'><h1>◆ FLASH-P</h1><div class='sub'>{html.escape(subtitle)}</div></div>"
        f"<div class='wrap'>{body}<div class='foot'>{html.escape(footer)} · "
        f"<a href='https://flash-p.com'>flash-p.com</a></div></div></body></html>",
        encoding="utf-8",
    )
    return out


# ---- public entry ----------------------------------------------------------
def render(verb: str, network_name: str, net_dir: Path, top_n: int = 8) -> tuple[Path | None, Path | None]:
    net_dir = Path(net_dir)
    if verb == "gxe":
        return _render_gxe(network_name, net_dir, top_n)
    if verb == "epistasis":
        return _render_epistasis(network_name, net_dir, top_n)
    return None, None


def _render_gxe(name: str, net_dir: Path, top_n: int):
    d = _gxe_data(net_dir)
    if not d["rows"]:
        return None, None
    out_dir = net_dir / "gxe"
    # PNG: top hits
    cols = [("gene", .26, "l"), ("mode", .13, "l"), ("env", .27, "l"), ("GxE", .18, "r"), ("@env", .16, "r")]
    rows, accent = [], []
    for r in d["hits"][:top_n]:
        g = _f(r.get("gxe_alg"))
        rows.append(([r.get("gene", ""), r.get("gene_mode", ""), r.get("env", ""),
                      f"{g:+.2f}", f'{_f(r.get("log2fc_gene_env_alg")):+.2f}'],
                     [TEXT, MUTED, TEXT, POS if g >= 0 else NEG, MUTED]))
        accent.append(POS if g >= 0 else NEG)
    agree = f'{d["agreement"]*100:.0f}%' if d["agreement"] is not None else "n/a"
    footer = f'{d["n_sig"]} significant GxE · envs: {", ".join(d["envs"])[:46]} · alg/ODE sign agree {agree}'
    png = _render_png(out_dir / "gxe_card.png", f"GxE · {name}", "Top gene × environment interactions",
                      cols, rows, accent, footer)
    # HTML: full top table
    body = []
    rows_html = "".join(
        f"<tr><td>{html.escape(r.get('gene',''))}</td><td>{html.escape(r.get('gene_mode',''))}</td>"
        f"<td>{html.escape(r.get('env',''))}</td><td>{_num(r.get('gxe_alg'))}</td>"
        f"<td>{_num(r.get('log2fc_gene_ambient_alg'))}</td><td>{_num(r.get('log2fc_gene_env_alg'))}</td></tr>"
        for r in d["hits"][:40]
    )
    body.append("<h2>Top gene × environment interactions</h2>")
    body.append(_html_table(["gene", "mode", "env", "GxE (alg)", "LFC @ambient", "LFC @env"], [rows_html]))
    html_out = _render_html(out_dir / "gxe_report.html", f"GxE · {name}", body, footer)
    return png, html_out


def _render_epistasis(name: str, net_dir: Path, top_n: int):
    d = _epi_data(net_dir)
    if not d["rows"]:
        return None, None
    out_dir = net_dir / "epistasis"
    cols = [("pair A", .30, "l"), ("pair B", .30, "l"), ("class", .22, "l"), ("ε", .18, "r")]
    rows, accent = [], []
    for r in d["genuine"][:top_n]:
        cls = r.get("interaction_class", "")
        eps = _f(r.get("epistasis_algebraic"))
        rows.append(([f'{r.get("node_A","")}:{r.get("mode_A","")}', f'{r.get("node_B","")}:{r.get("mode_B","")}',
                      cls, f"{eps:+.2f}"], [TEXT, TEXT, CLASS_COLORS.get(cls, TEXT), TEXT]))
        accent.append(CLASS_COLORS.get(cls, MUTED))
    cc = d["classes"]
    breakdown = " · ".join(f"{k} {cc[k]}" for k in ("synergy", "buffering", "reshaping", "masking", "additive") if cc.get(k))
    footer = f'{d["n_pairs"]} double perturbations · {breakdown}'
    png = _render_png(out_dir / "epistasis_card.png", f"epistasis · {name}",
                      "Top genuine gene × gene interactions", cols, rows, accent, footer)
    # HTML
    body = ["<h2>Interaction class breakdown</h2>"]
    pills = "".join(
        f'<tr><td><span class="pill" style="background:{CLASS_COLORS.get(k,MUTED)}">{k}</span></td>'
        f"<td>{cc[k]}</td></tr>" for k, _ in cc.most_common()
    )
    body.append(_html_table(["class", "count"], [pills]))
    body.append("<h2>Top genuine interactions (buffering · synergy · reshaping)</h2>")
    g_html = "".join(
        f'<tr><td>{html.escape(r.get("node_A",""))}:{html.escape(r.get("mode_A",""))}</td>'
        f'<td>{html.escape(r.get("node_B",""))}:{html.escape(r.get("mode_B",""))}</td>'
        f'<td><span class="pill" style="background:{CLASS_COLORS.get(r.get("interaction_class",""),MUTED)}">{html.escape(r.get("interaction_class",""))}</span></td>'
        f'<td>{_num(r.get("epistasis_algebraic"))}</td><td>{_num(r.get("log2fc_A_algebraic"))}</td>'
        f'<td>{_num(r.get("log2fc_B_algebraic"))}</td><td>{_num(r.get("log2fc_AB_algebraic"))}</td></tr>'
        for r in d["genuine"][:40]
    )
    body.append(_html_table(["A", "B", "class", "ε (alg)", "L(A)", "L(B)", "L(AB)"], [g_html]))
    html_out = _render_html(out_dir / "epistasis_report.html", f"epistasis · {name}", body, footer)
    return png, html_out


if __name__ == "__main__":  # quick manual test: python render.py <verb> <network_dir>
    import sys
    v, nd = sys.argv[1], Path(sys.argv[2])
    p, h = render(v, nd.name, nd)
    print("png :", p)
    print("html:", h)
