(() => {
  const properties = ['color', 'background-color', 'background-image', 'mask-image',
    'border-top-color', 'border-top-width', 'border-top-style', 'border-radius', 'box-shadow',
    'padding', 'margin', 'gap', 'width', 'height', 'min-width', 'min-height', 'max-width',
    'font-family', 'font-size', 'font-weight', 'font-style', 'font-stretch', 'font-variation-settings',
    'line-height', 'letter-spacing', 'text-transform', 'opacity', 'outline', 'outline-offset',
    'clip-path', 'filter', 'transform', 'transition', 'animation', 'fill', 'stroke',
    'display', 'position', 'inset', 'z-index', 'isolation', 'mix-blend-mode', 'background-blend-mode',
    'background-size', 'background-position', 'background-origin', 'background-clip',
    'overflow', 'overflow-x', 'overflow-y', 'box-sizing', 'align-items', 'justify-content',
    'row-gap', 'column-gap', 'min-block-size', 'max-height', 'aspect-ratio',
    'border-right', 'border-bottom', 'border-left', 'border-top', 'border-image',
    'padding-top', 'padding-right', 'padding-bottom', 'padding-left',
    'font-feature-settings', 'font-optical-sizing', 'text-decoration', 'text-align',
    'white-space', 'text-overflow', 'vertical-align', 'transform-origin', 'perspective',
    'backdrop-filter', 'mask-size', 'mask-position', 'mask-composite', 'pointer-events', '-webkit-text-security'];
  const facts = (style) => Object.fromEntries([...properties,
    ...Array.from(style).filter((name) => name.startsWith('--'))]
    .map((name) => [name, style.getPropertyValue(name)]));
  const identity = (element) => element.id ? `#${CSS.escape(element.id)}` :
    element === document.documentElement ? 'html' :
      `${identity(element.parentElement)} > ${element.localName}:nth-child(${Array.from(element.parentElement.children).indexOf(element) + 1})`;
  const resourceUrls = (css) => Array.from(css.matchAll(/url\(\s*(?:"([^"]*)"|'([^']*)'|([^)]*))\s*\)/g),
    (match) => match[1] ?? match[2] ?? match[3].trim());
  const appendResources = (resources, css, origin, base) => {
    for (const url of resourceUrls(css)) resources.push({ url, base, origin });
  };
  const pseudoFacts = (element, resources) => {
    const pseudo = {};
    for (const suffix of ['::before', '::after']) {
      const style = getComputedStyle(element, suffix);
      if (style.content !== 'none' && style.content !== 'normal') {
        const literal = /^"[^"\\]*"$/.test(style.content) ? style.content.slice(1, -1) : null;
        pseudo[suffix] = { content: style.content, ...facts(style),
          textRuns: literal ? [{ text: literal }] : [],
          unresolvedText: literal === null && !style.content.startsWith('url(') };
        appendResources(resources, style.backgroundImage, `${identity(element)}${suffix}`, document.baseURI);
        appendResources(resources, style.maskImage, `${identity(element)}${suffix}`, document.baseURI);
      }
    }
    return pseudo;
  };
  const nativeText = (element, style) => {
    if (!element.matches('input, textarea, select')) return null;
    if (element.matches('input, textarea') && element.matches(':placeholder-shown')) {
      const placeholder = getComputedStyle(element, '::placeholder');
      const masked = !['', 'none'].includes(placeholder.getPropertyValue('-webkit-text-security'));
      return { textRuns: [], placeholder: { ...facts(placeholder),
        textRuns: masked ? [] : [{ text: element.placeholder }], unresolvedText: masked } };
    }
    if (element.type === 'password' || !['', 'none'].includes(style.getPropertyValue('-webkit-text-security'))) {
      return { textRuns: [], unresolvedText: Boolean(element.value), nativeText: { kind: 'masked', glyphs: 'unknown' } };
    }
    if (element.tagName === 'TEXTAREA' || (element.tagName === 'INPUT' &&
        ['text', 'email', 'url', 'tel', 'search', 'button', 'submit', 'reset'].includes(element.type))) {
      return { textRuns: element.value ? [{ text: element.value, origin: 'control-value' }] : [],
        unresolvedText: !element.value && ['submit', 'reset'].includes(element.type) };
    }
    if (element.tagName === 'SELECT' && !element.multiple && element.size <= 1) {
      return { textRuns: element.selectedOptions.length ? [{ text: element.selectedOptions[0].label, origin: 'selected-option' }] : [] };
    }
    return { textRuns: [], unresolvedText: Boolean(element.value), nativeText: { kind: 'native-format', glyphs: 'unknown' } };
  };
  const nodeFacts = (root, resources, composition) => composition.visible
    .filter((candidate) => !candidate.pseudo && candidate.captureBounds.w > 0 && candidate.captureBounds.h > 0)
    .map((visibility) => {
    const element = document.querySelector(visibility.selector);
    const selector = visibility.selector;
    for (const property of ['background-image', 'mask-image', 'list-style-image']) {
      appendResources(resources, getComputedStyle(element).getPropertyValue(property), selector, document.baseURI);
    }
    if (element.localName === 'img') {
      resources.push({ origin: selector, base: document.baseURI, url: element.currentSrc || element.src,
        src: element.getAttribute('src'), srcset: element.getAttribute('srcset'),
        loaded: element.complete && element.naturalWidth > 0 });
    }
    const box = element.getBoundingClientRect();
    const style = getComputedStyle(element);
    const contentExtent = (axis, sides) => {
      const extent = parseFloat(style.getPropertyValue(axis));
      const edges = style.boxSizing === 'border-box' ? sides.reduce((sum, side) => sum +
        parseFloat(style.getPropertyValue(`padding-${side}`)) + parseFloat(style.getPropertyValue(`border-${side}-width`)), 0) : 0;
      return Number.isFinite(extent - edges) ? extent - edges : null;
    };
    const textRuns = Array.from(element.childNodes).filter((node) => node.nodeType === Node.TEXT_NODE && node.textContent.trim())
      .map((node) => {
        const range = document.createRange();
        range.selectNodeContents(node);
        return { text: node.textContent, rects: Array.from(range.getClientRects(), (rect) =>
          ({ x: rect.x, y: rect.y, width: rect.width, height: rect.height })) };
      });
    const native = nativeText(element, style);
    const pseudo = pseudoFacts(element, resources);
    if (native?.placeholder) pseudo['::placeholder'] = native.placeholder;
    const { placeholder, ...controlText } = native || {};
    const captured = visibility.captureBounds;
    const partial = captured.w < visibility.bounds.w || captured.h < visibility.bounds.h;
    const textVisibilityUncertain = partial || style.clipPath !== 'none' ||
      (native && (element.scrollWidth > element.clientWidth || element.scrollHeight > element.clientHeight));
    for (const occurrence of Object.values(pseudo)) occurrence.textVisibilityUncertain = Boolean(textVisibilityUncertain);
    return { selector, tag: element.localName, textRuns, ...controlText, visibility,
      textVisibilityUncertain: Boolean(textVisibilityUncertain),
      relation: root.contains(element) ? 'screen' : element.contains(root) ? 'ancestor' : 'outside',
      locale: element.closest('[lang]')?.getAttribute('lang') || document.documentElement.lang,
      box: { x: box.x, y: box.y, width: box.width, height: box.height },
      content: { width: contentExtent('width', ['left', 'right']), height: contentExtent('height', ['top', 'bottom']) },
      paddingBox: { width: element.clientWidth, height: element.clientHeight },
      state: { disabled: element.matches(':disabled'), selected: element.getAttribute('aria-selected'),
        pressed: element.getAttribute('aria-pressed'), checked: element.matches(':checked'),
        focus: element.matches(':focus'), hover: element.matches(':hover') },
      computed: facts(getComputedStyle(element)), pseudo };
  });
  const cssFacts = (resources) => {
    const rules = [], unavailableSheets = [], seenSheets = new Set();
    const readRules = (sheet, ancestors = []) => {
      if (seenSheets.has(sheet)) return;
      seenSheets.add(sheet);
      const base = sheet.href || document.baseURI;
      let accessible;
      try { accessible = sheet.cssRules; }
      catch (error) { unavailableSheets.push({ base, error: error.name }); return; }
      const visit = (cssRules, groups) => {
        for (const rule of cssRules) {
          if (rule.styleSheet) { readRules(rule.styleSheet, groups); continue; }
          rules.push({ base, groups, type: rule.constructor.name, css: rule.cssText,
            ...(rule.constructor.name === 'CSSFontFaceRule' ? { face: Object.fromEntries(
              ['font-family', 'src', 'font-weight', 'font-style', 'font-stretch', 'unicode-range',
                'font-display', 'font-feature-settings', 'font-variation-settings'].map((name) =>
                [name, rule.style.getPropertyValue(name)])) } : {}) });
          if (rule.cssRules) {
            visit(rule.cssRules, [...groups, rule.conditionText || rule.name || rule.constructor.name]);
          } else {
            appendResources(resources, rule.cssText, rule.selectorText || rule.constructor.name, base);
          }
        }
      };
      visit(accessible, ancestors);
    };
    for (const sheet of document.styleSheets) readRules(sheet);
    return { rules, unavailableSheets };
  };
  const svgFacts = (root) => [...(root.localName === 'svg' ? [root] : []), ...root.querySelectorAll('svg')].map((svg) => {
    const style = getComputedStyle(svg);
    const references = [svg, ...svg.querySelectorAll('*')].flatMap((element) =>
      Array.from(element.attributes).flatMap((attribute) => {
        const urls = resourceUrls(attribute.value);
        if (attribute.localName === 'href') urls.push(attribute.value);
        return urls.filter(Boolean);
      }));
    const ids = new Set([svg.id, ...Array.from(svg.querySelectorAll('[id]'), (element) => element.id)]);
    return { selector: identity(svg), markup: svg.outerHTML,
      inherited: { color: style.color, fill: style.fill, stroke: style.stroke, fontFamily: style.fontFamily },
      currentColor: /currentcolor/i.test(svg.outerHTML), references,
      unresolved: references.filter((reference) => !reference.startsWith('#') || !ids.has(reference.slice(1))) };
  });
  const fontFacts = () => ({ status: document.fonts.status, faces: Array.from(document.fonts, (face) => ({
    family: face.family, weight: face.weight, style: face.style, stretch: face.stretch,
    unicodeRange: face.unicodeRange, status: face.status })) });
  const dependencies = () => [...Array.from(document.scripts, (script) => script.src).filter(Boolean),
    ...Array.from(document.styleSheets, (sheet) => sheet.href).filter(Boolean),
    ...performance.getEntriesByType('resource').map((entry) => entry.name)];
  const redactMaskedLayout = (tree) => {
    if (!tree) return;
    if (['input', 'textarea'].includes(tree.tag)) {
      delete tree.value;
      delete tree.text;
      if (tree.type === 'password') tree.nativeText = { kind: 'masked', glyphs: 'unknown' };
    }
    for (const child of tree.children || []) redactMaskedLayout(child);
  };
  globalThis.captureFoundations = ({ selector, profile, captureTarget }) => {
    if (typeof layoutTree !== 'function' || typeof captureComposition !== 'function') {
      throw new Error('Load the shared layout-tree.js first');
    }
    const root = document.querySelector(selector);
    if (!root) throw new Error(`nothing matches ${selector}`);
    const composition = captureComposition(selector, { captureTarget });
    redactMaskedLayout(composition.screen.tree);
    redactMaskedLayout(composition.capture.tree);
    const outside = Array.from(new Set(composition.outsideScreen.map((candidate) =>
      document.querySelector(candidate.selector.replace(/::(?:before|after)$/, ''))).filter(Boolean)));
    const resources = [], nodes = nodeFacts(root, resources, composition), css = cssFacts(resources);
    const inlineSvg = Array.from(new Map([root, ...outside].flatMap(svgFacts).map((svg) => [svg.selector, svg])).values());
    return { schemaVersion: 2, source: document.URL, base: document.baseURI, profile,
      viewport: { width: innerWidth, height: innerHeight, dpr: devicePixelRatio },
      layout: composition.screen.tree, composition,
      rootVariables: facts(getComputedStyle(document.documentElement)), nodes, ...css, resources,
      inlineSvg, fonts: fontFacts(), dependencies: dependencies(),
      limitations: ['one observed profile only', 'CSS URL candidates require source review',
        'SVG markup needs inherited styles and external defs resolved', 'glyph fallback needs font-byte inspection',
        'iframes and shadow roots require separate inspection',
        'native masked/formatted and partially clipped text needs rendered glyph evidence',
        'visible candidates reuse composition bounds/hit tests; these are not pixel glyph visibility proof'] };
  };
})();
