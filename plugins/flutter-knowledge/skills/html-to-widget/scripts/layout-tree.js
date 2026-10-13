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

function captureComposition(target, options) {
  const opts = Object.assign({}, options || {});
  const resolve = (value) => {
    const element = typeof value === 'string' ? document.querySelector(value) : value;
    if (!(element instanceof Element)) throw new Error('captureComposition: nothing matches ' + value);
    return element;
  };
  const screen = resolve(target);
  const capture = opts.captureTarget == null ? null : resolve(opts.captureTarget);
  const viewportBox = { x: 0, y: 0, w: innerWidth, h: innerHeight };
  const round = (value) => Math.round(value * 10) / 10;
  const bounds = (box) => ({ x: round(box.left), y: round(box.top), w: round(box.width), h: round(box.height) });
  const intersect = (a, b) => {
    const x = Math.max(a.x, b.x);
    const y = Math.max(a.y, b.y);
    return { x, y, w: Math.max(0, Math.min(a.x + a.w, b.x + b.w) - x),
      h: Math.max(0, Math.min(a.y + a.h, b.y + b.h) - y) };
  };
  const hasArea = (box) => box.w > 0 && box.h > 0;
  const contains = (outer, inner) => inner.x >= outer.x && inner.y >= outer.y &&
    inner.x + inner.w <= outer.x + outer.w && inner.y + inner.h <= outer.y + outer.h;
  const identity = (element) => {
    if (element.id && document.querySelectorAll('#' + CSS.escape(element.id)).length === 1) {
      return '#' + CSS.escape(element.id);
    }
    const parts = [];
    for (let node = element; node instanceof Element; node = node.parentElement) {
      const index = node.parentElement ? [...node.parentElement.children].indexOf(node) + 1 : 1;
      parts.unshift(node.tagName.toLowerCase() + ':nth-child(' + index + ')');
    }
    return parts.join(' > ');
  };
  const relation = (element) => screen.contains(element) ? 'screen' : element.contains(screen) ? 'ancestor' : 'outside';
  const rendered = (element, style) => {
    if (['hidden', 'collapse'].includes(style.visibility) || style.display === 'none') return false;
    for (let node = element; node; node = node.parentElement) {
      const value = getComputedStyle(node);
      if (value.display === 'none' || Number(value.opacity) === 0 || value.contentVisibility === 'hidden') return false;
    }
    return true;
  };
  const createsContainingBlock = (style) => style.transform !== 'none' || style.perspective !== 'none' ||
    style.filter !== 'none' || /paint|layout|strict|content/.test(style.contain) ||
    /transform|perspective|filter/.test(style.willChange);
  const clippedBounds = (element, box, position) => {
    let result = intersect(box, viewportBox);
    let applyClip = !['fixed', 'absolute'].includes(position);
    for (let node = element.parentElement; node; node = node.parentElement) {
      const style = getComputedStyle(node);
      if (node === element.offsetParent && position === 'absolute') applyClip = true;
      if (createsContainingBlock(style)) applyClip = true;
      if (!applyClip) continue;
      const rect = node.getBoundingClientRect();
      const clip = { x: rect.left + node.clientLeft, y: rect.top + node.clientTop,
        w: node.clientWidth, h: node.clientHeight };
      const paintClip = /paint|strict|content/.test(style.contain);
      if (paintClip || style.overflowX !== 'visible') result = intersect(result, { ...clip, y: result.y, h: result.h });
      if (paintClip || style.overflowY !== 'visible') result = intersect(result, { ...clip, x: result.x, w: result.w });
    }
    return result;
  };
  const exposed = (element, box) => [0.1, 0.5, 0.9].some((x) => [0.1, 0.5, 0.9].some((y) => {
    const hit = document.elementFromPoint(box.x + box.w * x, box.y + box.h * y);
    return hit === element || element.contains(hit);
  }));
  const styleFacts = (style) => ({ position: style.position, zIndex: style.zIndex, display: style.display,
    opacity: style.opacity, overflowX: style.overflowX, overflowY: style.overflowY,
    color: style.color, background: style.background, border: style.border,
    boxShadow: style.boxShadow, transform: style.transform, clipPath: style.clipPath });
  const captureBox = capture ? bounds(capture.getBoundingClientRect()) : viewportBox;
  const captureVisibleBox = intersect(captureBox, viewportBox);
  const visible = [];
  const unresolvedDecorations = [];
  const record = (element, style, box, extra) => {
    const visibleBox = clippedBounds(element, box, style.position);
    if (!hasArea(visibleBox)) return;
    const control = element.matches('button, input:not([type="hidden"]), textarea, select, a[href], summary, [role="button"], [role="tab"], [role="checkbox"], [role="switch"], [role="textbox"]');
    const hitTestable = style.pointerEvents !== 'none';
    if (!extra && control && hitTestable && !exposed(element, visibleBox)) return;
    visible.push({ selector: identity(element), tag: element.tagName.toLowerCase(),
      relation: relation(element), role: element.getAttribute('role'), bounds: box,
      visibleBounds: visibleBox, captureBounds: intersect(visibleBox, captureVisibleBox),
      inCapture: contains(captureVisibleBox, visibleBox), control: !extra && control,
      hitTestable: !extra && hitTestable, styles: styleFacts(style), ...extra });
  };
  const pseudoBounds = (element, style) => {
    if (style.transform !== 'none' || style.position !== 'fixed' || !/^\d+(\.\d+)?px$/.test(style.width) ||
        !/^\d+(\.\d+)?px$/.test(style.height)) return null;
    for (let node = element; node; node = node.parentElement) {
      if (createsContainingBlock(getComputedStyle(node))) return null;
    }
    const dimension = (axis) => parseFloat(style[axis]) || 0;
    const w = dimension('width') + (style.boxSizing === 'border-box' ? 0 :
      dimension('paddingLeft') + dimension('paddingRight') + dimension('borderLeftWidth') + dimension('borderRightWidth'));
    const h = dimension('height') + (style.boxSizing === 'border-box' ? 0 :
      dimension('paddingTop') + dimension('paddingBottom') + dimension('borderTopWidth') + dimension('borderBottomWidth'));
    const x = style.left !== 'auto' ? dimension('left') + dimension('marginLeft') :
      style.right !== 'auto' ? innerWidth - dimension('right') - dimension('marginRight') - w : null;
    const y = style.top !== 'auto' ? dimension('top') + dimension('marginTop') :
      style.bottom !== 'auto' ? innerHeight - dimension('bottom') - dimension('marginBottom') - h : null;
    return x == null || y == null ? null : { x, y, w, h };
  };
  for (const element of document.querySelectorAll('*')) {
    if (['SCRIPT', 'STYLE', 'TEMPLATE', 'NOSCRIPT', 'LINK', 'META', 'HEAD'].includes(element.tagName)) continue;
    const style = getComputedStyle(element);
    if (rendered(element, style)) record(element, style, bounds(element.getBoundingClientRect()));
    for (const pseudo of ['::before', '::after']) {
      const value = getComputedStyle(element, pseudo);
      if (['none', 'normal', ''].includes(value.content) || !rendered(element, value) || Number(value.opacity) === 0) continue;
      const selector = identity(element) + pseudo;
      const box = pseudoBounds(element, value);
      const facts = { selector, hostSelector: identity(element), pseudo, content: value.content,
        geometry: box ? 'computed-fixed-box' : 'unresolved', control: false };
      if (box) record(element, value, box, facts);
      else unresolvedDecorations.push({ ...facts, relation: relation(element), styles: styleFacts(value) });
    }
  }
  const outsideScreen = visible.filter((item) => item.relation !== 'screen');
  const omittedSelectors = outsideScreen.filter((item) => !item.inCapture).map((item) => item.selector);
  const selection = (element, value) => ({ selector: typeof value === 'string' ? value : identity(element),
    identity: identity(element), bounds: bounds(element.getBoundingClientRect()) });
  return {
    schemaVersion: 1,
    screen: { ...selection(screen, target), tree: layoutTree(screen, opts) },
    capture: { ...(capture ? selection(capture, opts.captureTarget) : { selector: null, identity: 'viewport', bounds: viewportBox }),
      visibleBounds: captureVisibleBox, containsScreen: contains(captureVisibleBox, bounds(screen.getBoundingClientRect())),
      omittedSelectors, hasOutsideScreenOmissions: omittedSelectors.length > 0,
      tree: capture ? layoutTree(capture, opts) : null },
    viewport: { width: innerWidth, height: innerHeight, dpr: devicePixelRatio, scrollX, scrollY,
      visualViewport: globalThis.visualViewport ? { width: visualViewport.width, height: visualViewport.height,
        offsetLeft: visualViewport.offsetLeft, offsetTop: visualViewport.offsetTop, scale: visualViewport.scale } : null },
    document: { url: location.href, locale: document.documentElement.lang,
      direction: getComputedStyle(screen).direction, fontsStatus: document.fonts.status },
    visible, outsideScreen, unresolvedDecorations,
    limitations: ['Bounds are CSS pixels relative to the current viewport.',
      'Geometry and sampled control hit tests are not a pixel visibility proof; inspect the captured PNG.',
      'Shadows, complex clips, transformed pseudo-elements, iframe documents and shadow roots require separate inspection.'],
  };
}

globalThis.captureComposition = captureComposition;
