#!/usr/bin/env python3
"""Regenerate fixture_files/design/prototype.html, the HTML prototype used by task g1.

Usage: make_prototype.py   (needs fontTools: python3 -m pip install fonttools)

The prototype imitates a standalone design export: the real CSS and markup sit in a JS
string with '#', '<' and '>' escaped, and are injected at load time, so grepping the file
finds only the template's decoy tokens. Its font, "Nordvik Sans" (a small pixel font drawn
here, weights 400 and 700), is embedded as zlib-compressed base64 in an asset map keyed by
uuid, the second layout the design-from-html-flutter playbook describes.
Output is deterministic; only rebuild it on purpose, since runs on different prototypes
are not comparable.
"""
import base64, io, json, os, zlib
from fontTools.fontBuilder import FontBuilder
from fontTools.pens.ttGlyphPen import TTGlyphPen

HERE = os.path.dirname(os.path.abspath(__file__))

# 5x7 bitmaps of the characters the prototype shows; lowercase reuses them at x-height.
G = '''
A .###. #...# #...# ##### #...# #...# #...#
B ####. #...# #...# ####. #...# #...# ####.
C .###. #...# #.... #.... #.... #...# .###.
D ####. #...# #...# #...# #...# #...# ####.
E ##### #.... #.... ####. #.... #.... #####
F ##### #.... #.... ####. #.... #.... #....
G .###. #...# #.... #.### #...# #...# .###.
H #...# #...# #...# ##### #...# #...# #...#
I .###. ..#.. ..#.. ..#.. ..#.. ..#.. .###.
J ..### ...#. ...#. ...#. ...#. #..#. .##..
K #...# #..#. #.#.. ##... #.#.. #..#. #...#
L #.... #.... #.... #.... #.... #.... #####
M #...# ##.## #.#.# #.#.# #...# #...# #...#
N #...# #...# ##..# #.#.# #..## #...# #...#
O .###. #...# #...# #...# #...# #...# .###.
P ####. #...# #...# ####. #.... #.... #....
Q .###. #...# #...# #...# #.#.# #..#. .##.#
R ####. #...# #...# ####. #.#.. #..#. #...#
S .#### #.... #.... .###. ....# ....# ####.
T ##### ..#.. ..#.. ..#.. ..#.. ..#.. ..#..
U #...# #...# #...# #...# #...# #...# .###.
V #...# #...# #...# #...# #...# .#.#. ..#..
W #...# #...# #...# #.#.# #.#.# #.#.# .#.#.
X #...# #...# .#.#. ..#.. .#.#. #...# #...#
Y #...# #...# .#.#. ..#.. ..#.. ..#.. ..#..
Z ##### ....# ...#. ..#.. .#... #.... #####
0 .###. #...# #..## #.#.# ##..# #...# .###.
1 ..#.. .##.. ..#.. ..#.. ..#.. ..#.. .###.
2 .###. #...# ....# ...#. ..#.. .#... #####
3 ##### ...#. ..#.. ...#. ....# #...# .###.
4 ...#. ..##. .#.#. #..#. ##### ...#. ...#.
5 ##### #.... ####. ....# ....# #...# .###.
6 ..##. .#... #.... ####. #...# #...# .###.
7 ##### ....# ...#. ..#.. .#... .#... .#...
8 .###. #...# #...# .###. #...# #...# .###.
9 .###. #...# #...# .#### ....# ...#. .##..
. ..... ..... ..... ..... ..... .##.. .##..
, ..... ..... ..... ..... .##.. ..#.. .#...
- ..... ..... ..... .###. ..... ..... .....
$ ..#.. .#### #.#.. .###. ..#.# ####. ..#..
'''
BITMAPS = {line.split()[0]: line.split()[1:] for line in G.strip().splitlines()}


def glyph(rows, px_h, extra):
    pen = TTGlyphPen(None)
    for r, row in enumerate(rows):
        for c, on in enumerate(row):
            if on == '#':
                x0, y0 = 50 + c * 100, (6 - r) * px_h
                x1, y1 = x0 + 100 + extra, y0 + px_h
                pen.moveTo((x0, y0)); pen.lineTo((x0, y1)); pen.lineTo((x1, y1)); pen.lineTo((x1, y0)); pen.closePath()
    return pen.glyph()


def build(weight, style, extra):
    cmap, glyphs, widths = {32: 'space'}, {'.notdef': glyph(BITMAPS['I'], 100, extra), 'space': TTGlyphPen(None).glyph()}, {'.notdef': 600, 'space': 400}
    for ch, rows in BITMAPS.items():
        name = 'u%04X' % ord(ch)
        glyphs[name], widths[name], cmap[ord(ch)] = glyph(rows, 100, extra), 600 + extra, name
        if ch.isalpha():
            low = 'u%04X' % ord(ch.lower())
            glyphs[low], widths[low], cmap[ord(ch.lower())] = glyph(rows, 74, extra), 600 + extra, low
    names = ['.notdef', 'space'] + sorted(n for n in glyphs if n not in ('.notdef', 'space'))
    fb = FontBuilder(1000, isTTF=True)
    fb.setupGlyphOrder(names)
    fb.setupCharacterMap(cmap)
    fb.setupGlyf(glyphs)
    fb.setupHorizontalMetrics({n: (widths[n], 50) for n in names})
    fb.setupHorizontalHeader(ascent=900, descent=-250)
    fb.setupNameTable({'familyName': 'Nordvik Sans', 'styleName': style,
                       'copyright': 'Copyright 2026 Wayfare Studio', 'manufacturer': 'Wayfare Studio',
                       'designer': 'Wayfare Studio', 'uniqueFontIdentifier': 'WayfareStudio: Nordvik Sans %s: 2026' % style,
                       'fullName': 'Nordvik Sans %s' % style, 'psName': 'NordvikSans-%s' % style, 'version': 'Version 1.000'})
    fb.setupOS2(sTypoAscender=900, sTypoDescender=-250, usWinAscent=900, usWinDescent=250, usWeightClass=weight,
                fsSelection=0x20 if weight == 700 else 0x40)
    fb.setupPost()
    fb.setupHead(unitsPerEm=1000, created=0, modified=0, macStyle=1 if weight == 700 else 0)
    buf = io.BytesIO()
    fb.save(buf)
    return buf.getvalue()


FONT_IDS = {'Regular': '7f3c9a1e-52b4-4d0e-9c61-0b8e2f4a7d13', 'Bold': 'c2d84b06-9e1f-4a73-b5d2-6f0a3c8e1b95'}

TEMPLATE = r'''<style>
@font-face{font-family:"Nordvik Sans";font-weight:400;font-style:normal;src:url("%(Regular)s") format("truetype")}
@font-face{font-family:"Nordvik Sans";font-weight:700;font-style:normal;src:url("%(Bold)s") format("truetype")}
:root{
  --bg-page:#F4F6F5;--surface:#FFFFFF;--surface-sunken:#EDF1EF;
  --fg-1:#0E1A17;--fg-2:#4A5A55;--fg-3:#83928D;
  --border:#D6DEDA;
  --primary:#0F766E;--on-primary:#FFFFFF;--primary-soft:rgba(15,118,110,0.12);
  --success:#15803D;--warning:#B45309;--danger:#B91C1C;
  --font-sans:"Nordvik Sans","Noto Sans Arabic",system-ui,sans-serif;
  --fs-display:28px;--lh-display:34px;--tr-display:-0.02em;
  --fs-title:20px;--lh-title:26px;--tr-title:-0.01em;
  --fs-body:15px;--lh-body:22px;--tr-body:0;
  --fs-caption:12px;--lh-caption:16px;--tr-caption:0.02em;
  --dur-fast:120ms;--dur-base:220ms;--dur-slow:360ms;
  --ease-standard:cubic-bezier(0.2,0,0,1);--ease-spring:cubic-bezier(0.34,1.56,0.64,1);
}
.app{font-family:var(--font-sans);background:var(--bg-page);color:var(--fg-1);min-height:100vh;padding:0 20px 32px;max-width:430px;margin:0 auto;box-sizing:border-box}
.t-display{font-size:var(--fs-display);line-height:var(--lh-display);letter-spacing:var(--tr-display);font-weight:700;margin:0}
.t-title{font-size:var(--fs-title);line-height:var(--lh-title);letter-spacing:var(--tr-title);font-weight:700;margin:0}
.t-body{font-size:var(--fs-body);line-height:var(--lh-body);letter-spacing:var(--tr-body);font-weight:400;color:var(--fg-2);margin:0}
.t-caption{font-size:var(--fs-caption);line-height:var(--lh-caption);letter-spacing:var(--tr-caption);font-weight:400;color:var(--fg-3);margin:0}
.header{padding:24px 0 16px}
.field{display:block;width:100%%;box-sizing:border-box;height:48px;border-radius:12px;border:1px solid var(--border);background:var(--surface-sunken);padding:0 14px;font:400 15px/22px var(--font-sans);color:var(--fg-1);transition:border-color var(--dur-base) var(--ease-standard),box-shadow var(--dur-base) var(--ease-standard)}
.field::placeholder{color:var(--fg-3)}
.field:focus{border-color:var(--primary);box-shadow:0 0 0 3px var(--primary-soft);outline:none}
.list{display:flex;flex-direction:column;gap:12px;margin:20px 0}
.card{background:var(--surface);border:1px solid var(--border);border-radius:16px;padding:16px;display:flex;flex-direction:column;gap:4px;animation:fade-up var(--dur-slow) var(--ease-standard) both}
.card:nth-child(2){animation-delay:60ms}.card:nth-child(3){animation-delay:120ms}
.card-row{display:flex;justify-content:space-between;align-items:center}
.badge{font-size:var(--fs-caption);line-height:var(--lh-caption);font-weight:700}
.badge.is-confirmed{color:var(--success)}.badge.is-pending{color:var(--warning)}.badge.is-cancelled{color:var(--danger)}
.btn-primary{display:block;width:100%%;height:52px;border-radius:14px;border:0;background:var(--primary);color:var(--on-primary);font:700 15px/20px var(--font-sans);box-shadow:0 6px 16px var(--primary-soft);cursor:pointer;transition:transform var(--dur-fast) var(--ease-spring),background-color var(--dur-base) var(--ease-standard)}
.btn-primary:active{transform:scale(.97)}
.btn-primary:disabled{opacity:.4}
@keyframes fade-up{from{opacity:0;transform:translateY(12px)}to{opacity:1;transform:none}}
</style>
<main class="app">
  <header class="header">
    <p class="t-caption">Wayfare</p>
    <h1 class="t-display">Your trips</h1>
  </header>
  <input class="field" type="search" placeholder="Search trips">
  <section class="list">
    <article class="card"><div class="card-row"><h2 class="t-title">Lisbon weekend</h2><span class="badge is-confirmed">Confirmed</span></div><p class="t-body">Lisbon, Portugal</p><p class="t-caption">12 - 14 Oct - $640</p></article>
    <article class="card"><div class="card-row"><h2 class="t-title">Oslo fjords</h2><span class="badge is-pending">Pending</span></div><p class="t-body">Bergen, Norway</p><p class="t-caption">2 - 9 Nov - $1,980</p></article>
    <article class="card"><div class="card-row"><h2 class="t-title">Cairo and Luxor</h2><span class="badge is-cancelled">Cancelled</span></div><p class="t-body">Cairo, Egypt</p><p class="t-caption">20 - 27 Dec - $1,150</p></article>
  </section>
  <button class="btn-primary" type="button">Plan a trip</button>
</main>'''

PAGE = '''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Wayfare - Trips</title>
<style>
:root{--primary:#3366FF;--bg-page:#FFFFFF;--radius-card:8px}
html,body{margin:0;background:var(--bg-page)}
#root:empty::before{content:"Loading";display:block;padding:24px;font:14px system-ui;color:#999999}
</style>
</head>
<body>
<div id="root"></div>
<script>window.__bundle=%s;</script>
<script>
(async()=>{
  const b=window.__bundle;
  let html=b.template;
  for(const [id,a] of Object.entries(b.assets)){
    let bytes=Uint8Array.from(atob(a.data),c=>c.charCodeAt(0));
    if(a.compressed){
      const s=new Blob([bytes]).stream().pipeThrough(new DecompressionStream('deflate'));
      bytes=new Uint8Array(await new Response(s).arrayBuffer());
    }
    html=html.split(id).join(URL.createObjectURL(new Blob([bytes],{type:a.mime})));
  }
  document.getElementById('root').innerHTML=html;
})();
</script>
</body>
</html>
'''


def main():
    assets = {}
    for (weight, style, extra), uid in zip(((400, 'Regular', 0), (700, 'Bold', 45)), FONT_IDS.values()):
        raw = build(weight, style, extra)
        assets[uid] = {'mime': 'font/ttf', 'compressed': True, 'data': base64.b64encode(zlib.compress(raw, 9)).decode()}
    bundle = {'assets': assets, 'template': TEMPLATE % FONT_IDS}
    js = json.dumps(bundle, separators=(',', ':'))
    js = js.replace('<', '\\u003c').replace('>', '\\u003e').replace('#', '\\u0023')
    out = os.path.join(HERE, 'fixture_files', 'design', 'prototype.html')
    with open(out, 'w') as f:
        f.write(PAGE % js)
    print('wrote', out)


if __name__ == '__main__':
    main()
