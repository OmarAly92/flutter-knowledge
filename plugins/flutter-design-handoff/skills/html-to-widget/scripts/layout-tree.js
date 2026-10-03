function layoutTree(target, options) {
  const opts = Object.assign({ hidden: false, maxText: 80 }, options || {});
  const root = typeof target === 'string' ? document.querySelector(target) : target;
  if (!root) throw new Error('layoutTree: nothing matches ' + target);
  const origin = root.getBoundingClientRect();
  const SIDES = ['top', 'right', 'bottom', 'left'];
  const SKIP = ['SCRIPT', 'STYLE', 'TEMPLATE', 'NOSCRIPT', 'LINK', 'META'];

  const px = (v) => {
    const n = parseFloat(v);
    return Number.isFinite(n) ? Math.round(n * 10) / 10 : 0;
  };

  const canvas = document.createElement('canvas');
  canvas.width = canvas.height = 1;
  const ctx = canvas.getContext('2d', { willReadFrequently: true });
  const byte = (n) => n.toString(16).padStart(2, '0');

  const hex = (c) => {
    if (!c) return null;
    if (!CSS.supports('color', c)) return c;
    ctx.clearRect(0, 0, 1, 1);
    ctx.fillStyle = c;
    ctx.fillRect(0, 0, 1, 1);
    const [r, g, b, a] = ctx.getImageData(0, 0, 1, 1).data;
    if (a === 0) return null;
    return '#' + byte(r) + byte(g) + byte(b) + (a < 255 ? byte(a) : '');
  };

  const COLOR_FN = /\b(?:rgba?|hsla?|hwb|lab|lch|oklab|oklch|color)\([^()]*\)/g;
  const colorsIn = (v) => v.replace(COLOR_FN, (c) => hex(c) || '#00000000');

  const sides = (s, prop) => SIDES.map((k) => px(s.getPropertyValue(`${prop}-${k}`)));

  const border = (s) => {
    const parts = SIDES.map((k) => {
      const w = px(s.getPropertyValue(`border-${k}-width`));
      const style = s.getPropertyValue(`border-${k}-style`);
      return w && style !== 'none' ? `${w}px ${hex(s.getPropertyValue(`border-${k}-color`))}` : null;
    });
    if (!parts.some(Boolean)) return null;
    if (parts.every((p) => p === parts[0])) return parts[0];
    return Object.fromEntries(SIDES.map((k, i) => [k, parts[i]]).filter(([, v]) => v));
  };

  const corner = (v) => (v.trim().endsWith('%') && parseFloat(v) ? v.trim() : px(v));

  const radius = (s) => {
    const r = ['top-left', 'top-right', 'bottom-right', 'bottom-left'].map((k) => corner(s.getPropertyValue(`border-${k}-radius`)));
    if (!r.some(Boolean)) return null;
    return r.every((v) => v === r[0]) ? r[0] : r;
  };

  const ownText = (el) => [...el.childNodes]
    .filter((c) => c.nodeType === Node.TEXT_NODE)
    .map((c) => c.textContent)
    .join(' ')
    .replace(/\s+/g, ' ')
    .trim();

  const typography = (n, s) => {
    n.color = hex(s.color);
    n.font = {
      family: s.fontFamily.split(',')[0].replace(/["']/g, '').trim(),
      size: px(s.fontSize),
      weight: Number(s.fontWeight),
      lineHeight: s.lineHeight === 'normal' ? 'normal' : px(s.lineHeight),
    };
    if (s.letterSpacing !== 'normal') n.font.letterSpacing = px(s.letterSpacing);
    if (!['start', 'left'].includes(s.textAlign)) n.font.align = s.textAlign;
    if (s.textTransform !== 'none') n.font.transform = s.textTransform;
  };

  const pseudo = (el, which) => {
    const p = getComputedStyle(el, which);
    if (!p.content || p.content === 'none' || p.content === 'normal') return null;
    const out = { content: p.content, w: px(p.width), h: px(p.height) };
    const bg = hex(p.backgroundColor);
    if (bg) out.bg = bg;
    const r = radius(p);
    if (r) out.radius = r;
    return out;
  };

  const walk = (el) => {
    const s = getComputedStyle(el);
    const hidden = s.display === 'none' || s.visibility === 'hidden';
    if (hidden && !opts.hidden) return null;
    const box = el.getBoundingClientRect();
    const n = { tag: el.tagName.toLowerCase() };
    if (el.id) n.id = el.id;
    if (el.classList.length) n.cls = [...el.classList].join(' ');
    if (hidden) n.hidden = true;
    n.x = px(box.left - origin.left);
    n.y = px(box.top - origin.top);
    n.w = px(box.width);
    n.h = px(box.height);

    if (s.display !== 'block' && s.display !== 'inline') n.display = s.display;
    if (s.display.includes('flex')) {
      n.dir = s.flexDirection;
      if (s.flexWrap !== 'nowrap') n.wrap = s.flexWrap;
      if (!['normal', 'flex-start', 'start'].includes(s.justifyContent)) n.justify = s.justifyContent;
      if (!['normal', 'stretch'].includes(s.alignItems)) n.align = s.alignItems;
    }
    if (s.display.includes('grid')) n.columns = s.gridTemplateColumns;
    const rowGap = px(s.rowGap);
    const colGap = px(s.columnGap);
    if (rowGap || colGap) {
      if (rowGap === colGap) n.gap = rowGap;
      else Object.assign(n, { rowGap, colGap });
    }
    const grow = parseFloat(s.flexGrow);
    if (grow) n.grow = grow;
    if (parseFloat(s.flexShrink) === 0) n.shrink = 0;
    if (s.flexBasis !== 'auto') n.basis = s.flexBasis;
    if (s.alignSelf !== 'auto') n.self = s.alignSelf;

    if (s.position !== 'static') {
      n.position = s.position;
      if (s.position === 'absolute' || s.position === 'fixed') {
        const [t, r, b, l] = SIDES.map((k) => px(s[k]));
        if (t <= b) n.top = t; else n.bottom = b;
        if (l <= r) n.left = l; else n.right = r;
      } else {
        if (px(s.top)) n.top = px(s.top);
        if (px(s.left)) n.left = px(s.left);
      }
      if (s.zIndex !== 'auto') n.z = Number(s.zIndex);
    }
    if (s.transform !== 'none') n.transform = s.transform;

    const padding = sides(s, 'padding');
    if (padding.some(Boolean)) n.padding = padding;
    const margin = sides(s, 'margin');
    if (margin.some(Boolean)) n.margin = margin;
    const b = border(s);
    if (b) n.border = b;
    const r = radius(s);
    if (r) n.radius = r;
    const bg = hex(s.backgroundColor);
    if (bg) n.bg = bg;
    if (s.backgroundImage !== 'none') n.bgImage = colorsIn(s.backgroundImage);
    if (s.boxShadow !== 'none') n.shadow = colorsIn(s.boxShadow);
    if (parseFloat(s.opacity) < 1) n.opacity = parseFloat(s.opacity);
    if (s.overflow !== 'visible') n.overflow = s.overflow;

    const text = ownText(el);
    if (text) {
      n.text = text.length > opts.maxText ? text.slice(0, opts.maxText) + '\u2026' : text;
      typography(n, s);
    }
    if (n.tag === 'input' || n.tag === 'textarea') {
      n.type = el.type;
      if (el.placeholder) n.placeholder = el.placeholder;
      if (el.value) n.value = el.type === 'password' ? '\u2022'.repeat(el.value.length) : el.value;
      typography(n, s);
    }
    if (n.tag === 'img') n.src = el.getAttribute('src');
    for (const which of ['::before', '::after']) {
      const p = pseudo(el, which);
      if (p) n[which.slice(2)] = p;
    }
    if (n.tag === 'svg') return n;

    const children = [...el.children].filter((c) => !SKIP.includes(c.tagName)).map(walk).filter(Boolean);
    if (children.length) n.children = children;
    return n;
  };

  return walk(root);
}

globalThis.layoutTree = layoutTree;
