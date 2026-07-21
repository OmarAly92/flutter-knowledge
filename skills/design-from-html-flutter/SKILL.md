---
name: design-from-html-flutter
description: Use when the user provides an HTML design prototype (standalone HTML file, exported mockup, or URL) and wants a Flutter app to match it 100% — setting the skin/theme colors, fonts and text styles, motion constants, core widgets, or generating per-screen design docs and implementation prompts from that design. Triggers - "check the design html", "set the skin like the html", "match the design", "extract the design tokens", "design-first", "make design docs for each screen", "prompt md for each screen".
---

# Design-First From HTML

Turn an HTML design prototype into (1) a fully populated app design system, (2) design-styled
core widgets, and (3) per-screen documentation + implementation prompts that let cleared-session
agents build every screen pixel-accurately. The prototype is the single source of truth —
**extract, never eyeball**.

## Phase order (each phase gates the next; run the project's analyzer/linter clean after each)

1. **Explore the prototype** — open it in a browser at mobile width (375×812) and walk EVERY
   screen and state by driving it with JS. Verify claimed behaviors live (gestures, navigation
   pattern) — never assume from appearance. See playbook §1.
2. **Skins/colors** — dump the CSS custom properties for every theme from the CSSOM, map them
   onto the project's skin/theme layer, delete zero-consumer template slots, add design-specific
   slots. See playbook §2.
3. **Fonts + text styles** — identify families from `@font-face`; extract embedded font data
   from the file when present (it usually is in standalone exports) before telling the user to
   download anything; wire the type scale (size/line-height/tracking per token). See playbook §3.
4. **Motion constants** — durations, cubic-bezier curves, keyframe offsets, transition usages →
   one motion constants class. See playbook §4.
5. **Core widgets** — dump every component CSS rule; restyle existing shared widgets and create
   the design's primitives, all consuming ONLY the skin/type/motion tokens. See playbook §5.
6. **Docs + prompts** — `docs/design/`: shared foundation docs + one dir per screen containing
   the full spec md, headless screenshots, and a self-contained `prompt.md` brief.
   See playbook §6 and templates.md.

**REQUIRED:** read [playbook.md](playbook.md) for the phase you are executing — it has the
extraction code and the traps. Doc structures live in [templates.md](templates.md).

**REQUIRED SUB-SKILL:** invoke `/flutter-knowledge` (the flutter-knowledge skill) before
writing any Dart — it is the authority on the project architecture (feature tree, Cubit
conventions, screen/body split, DI, routing, UI rules). Use `/add-translation` whenever a
user-facing string is added.

## Non-negotiables

- Every color/size/duration comes from the prototype's computed CSS — quote exact values.
- Feature code never sees raw hex/durations: everything flows through the skin, text-style,
  and motion token layers (add missing slots there instead).
- Screenshots are captured headlessly from the prototype itself, after animations settle.
- Behaviors documented as fact must be verified by driving the prototype, not inferred.

## Common mistakes (each one happened in the field)

| Mistake | Fix |
|---|---|
| Assuming the mobile nav pattern (e.g. "there must be a tab bar") | Interrogate the DOM + read the CSS comments; test gestures with drags |
| Grepping the raw HTML for CSS/fonts and finding nothing | Standalone exports escape content into JS strings — extract via the browser CSSOM, or regex the escaped text |
| Telling the user to download proprietary fonts | Check for base64/asset-map embedded fonts first and extract them |
| Screenshotting right after navigation | Entrance animations start at opacity 0 — wait ~1s, re-shoot |
| Restyling widgets from screenshots | Screenshots lie about borders/alpha — use the component CSS rules |
| Docs that only a warm session can use | Every screen dir gets a `prompt.md` that stands alone (see templates.md) |
