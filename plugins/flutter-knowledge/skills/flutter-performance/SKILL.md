---
name: flutter-performance
description: Use when writing Flutter lists/grids, image loading, animations or expensive build logic, investigating jank or excess memory/rebuilds, or reviewing a UI change with a concrete performance concern.
---

# Performance

Read the [configuration contract](../flutter-init/references/configuration.md). Preserve owner-held data, operation states, shared widgets and token/motion rules. Improve the implementation without inventing a second state or image-loading stack.

## At authoring time

Keep network work, parsing, substantial sorting/filtering and controller creation out of build. Compute data in its existing owner/layer and let UI render it. Use const where possible, while remembering inherited dependencies can still cause rebuilds. Keep extracted widgets in their own files and use the exact operation-state filtering required by `flutter-screen-ui`.

Use lazy builders for large/dynamic lists and stable domain keys for reordering. A short fixed list need not become a builder. Supply itemExtent only for genuinely uniform rows that remain correct under text scaling; don't force text rows to a fixed height to gain scroll performance.

## Images and animation

Reuse the configured/project loader. Size decoding to the rendered image and device pixel ratio where the loader supports it, and preserve placeholder geometry. Do not introduce cached_network_image merely because an image appears twice; verify the existing SDK/wrapper caching behavior first.

Use the existing motion tokens and animation wrappers. Keep static animation subtrees outside per-frame work where the chosen API permits it. Add RepaintBoundary when measurement shows independent painting will help; do not wrap every widget or disable list keep-alives/repaint boundaries without evidence.

## Diagnose before restructuring

Measure frame work, rebuilds and memory in profile mode when app execution is authorized. Compare the same device, data and interaction before/after. Do not declare a measured improvement from debug timings or guess the bottleneck from code length. When profiling is unavailable, distinguish the structural improvement from an unmeasured speed claim. [Flutter performance guidance](https://docs.flutter.dev/perf/best-practices), [rendering measurements](https://docs.flutter.dev/perf/rendering-performance).

Check that optimization preserves large text, RTL, semantics and the intended layout. Use the responsive/accessibility skills where those responsibilities intersect.
