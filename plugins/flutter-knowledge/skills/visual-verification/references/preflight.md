# Core and capture preflight

Run this before building the first design-backed screen and again when core or the capture harness changes. It finds shared-foundation and capture defects while they are cheap, instead of discovering them as red pixels in every row. It proves wiring, not design fidelity.

## Shared core

Prove the core actually works, not just that files exist. Exercise the project's own contracts through a focused test or the capture harness, using the configured mechanics:

- Resolve every core registration through the real app registration entry (consumer/client, network status, skin registry, preferences, logger, root state owners). An unregistered or differently scoped dependency fails here, not in the first feature.
- Build `AppTheme.of(skin)` for every built-in and JSON skin; read each token group through `context.tokens`; select a skin through its owner and see the root rebuild. A theme extension absent from `ThemeData` fails here.
- Load English and Arabic, resolve a key and a missing key, switch locale and confirm direction.
- Render the principal text, scaffold/app bar, container, spaces, buttons (enabled, disabled, loading), fields (focus, error), sheet and feedback wrappers under light/dark, both locales and a larger text scale.
- Drive the API consumer against a fake transport: success, wrapped and unwrapped envelope, validation error, timeout/cancel/connection failure mapping, and that the Failure boundary — not a transport type — leaves the data layer.
- Confirm a backend URL is an explicit configuration value; do not call a live server.

## Capture calibration

Before the full matrix, capture one or two representative source rows and read them at full resolution:

- The harness mounts the expected root and state. Assert it with finders (screen type, key text) so a wrong route, loading skeleton or error state fails the capture instead of producing a plausible image.
- Dimensions, DPR, safe area, skin, locale, text scale, pointer and focus come from the row's profile; nothing is inherited from a default.
- Fonts come from the project's bundled files for both scripts, never the test fallback. Compare glyph shapes and the wrapping of a long line against the source.
- Shadows are enabled and animations are advanced to the settled frame the source was captured at; a mid-transition drawer or sheet is not a settled state.
- Inputs show the intended text, caret and placeholder; loading rows show the intended frame.
- Source capture used the same profile and the extraction covered the whole capture boundary (see `captureComposition`). Content outside the screen subtree is implemented or consciously excluded.

Fix harness and shared-widget defects found here once, before they multiply across rows.

## Behavior checks before polish

Run the checks the feature actually has, before spending visual rounds:

- Pending operations: overlapping taps/submissions, a response arriving after a newer request, and the owner closed while a request is pending. No state is emitted after close; controllers and subscriptions are disposed.
- Drive the actual routed screens and controls: typing must update enabled/send actions, submission must show its pending state, and completion must show the new message or destination screen. Assert each visible transition; seeded owner state in a capture alone does not prove that descendants rebuild or route effects work.
- Combined layout: Arabic with larger text scale at a narrow width, with the keyboard open on a screen with fields. Automatic keyboard avoidance must work without capture/test scrolling helpers (including forced `ensureVisible`); production focus/inset management must be exercised as actual UI behavior and reported explicitly. Assert the actual field and caret stay inside the scroll viewport and above any fixed footer, rather than only above the keyboard. Verify inset consumption does not apply the keyboard twice. A deliberately scrolled capture is labeled and tested separately.
- Interaction targets keep their tap size and semantics under scale and RTL.

## Correction rhythm

Iterate with targeted rows, not the whole matrix: capture only affected rows with `run_verification.py`, compare, fix every known cause. After the changes settle run the complete manifest once as the final gate, then the repository's final review. Retain every attempt; do not edit a manifest or reference to make a row pass.
