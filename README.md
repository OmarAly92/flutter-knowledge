# Flutter Knowledge

One **`flutter-knowledge`** plugin for Flutter code conventions, design implementation,
visual verification and golden tests. All 22 skills live in one plugin.

Flutter/Dart skills for coding agents. Install once and your agent follows a
consistent set of full-stack Flutter conventions — feature architecture, the
data layer, Cubit state management, dependency injection, routing, the core UI
wrappers, and localization. `flutter-knowledge` is a small map of hard rules
that routes the agent to five core mini skills (`flutter-feature-structure`,
`flutter-data-layer`, `flutter-state-management`, `flutter-screen-ui`,
`flutter-routing-di`) before it writes each kind of code — plus on-demand
helpers: `add-translation`
for keeping `en.json` / `ar.json` in sync, `drift-local-database` and
`hive-local-database` for local persistence (drift/SQLite or Hive),
`flutter-testing` for mocktail/bloc_test unit tests, `flutter-app-theme` for
the theme layer (skin colors with light/dark switching, text styles, motion,
shapes and `ThemeData`). HTML/Figma source readers handle both immediate screen
implementation and whole-app planning through the shared workflow.

Each skill has a scoped `description` for task-based discovery. Outside Gemini,
the mini skills and helpers load on demand through those descriptions, the
`flutter-knowledge` map or an explicit `/<skill-name>` request. Description-based
selection depends on the host and agent; it does not guarantee invocation.

The configured Claude Code and Codex `SessionStart` hooks check for
`pubspec.yaml` and inject the map and hard rules. OpenCode adds them through
`experimental.chat.system.transform`; Pi detects the project at `session_start`
and adds them through `before_agent_start`. Cursor and Kimi rely on descriptions.
Gemini's `GEMINI.md` includes all 22 skills and shared references, so its context
loading differs from the on-demand hosts. These loading paths alone establish
neither prompt-cache behavior nor measured token savings.

## Use ordinary requests

Describe the result you want; skill names and slash commands are optional:

```text
Build the login screen from ./design/app.html.
The login UI changed in the design. Update the existing screen.
Apply the updated shared colors and fonts from ./design/app.html to the app theme.
```

The workflow selects the source reader, relevant conventions, visual comparison and review. Existing-screen updates preserve working logic and use the screen's known design source; if that source or screen is unclear, the agent asks for the missing identity. A local UI update stays scoped to that screen. App-wide theme requests use the foundation workflow after core exists. Design comparisons report measured differences and unresolved gaps; passing an old Flutter golden does not prove a match to the updated design.

The agent also checks the foundation before implementation. It automatically prepares shared core in a confirmed fresh app, completes only task-required gaps in an existing core, and reuses working equivalents. Planning and review remain read-only. You can still use `/flutter-core` to prepare or complete the whole foundation explicitly.

## Start with an existing Flutter project

After installing the plugin, open your Flutter project's root folder in your coding agent—the folder containing `pubspec.yaml`. The examples below are **agent-chat commands and requests**. Replace `./design/app.html` with your actual HTML design path; it may contain the whole app.

### 1. Initialize the project configuration

```text
/flutter-init
```

The agent reads the project's packages and source, then creates `flutter-knowledge.yaml`. For a confirmed empty Flutter starter, it also adds the selected packages to `pubspec.yaml` with compatible versions, puts test packages in `dev_dependencies`, and resolves the dependencies. An existing app keeps its current pubspec; initialization only updates configuration there. Review the choices and resolve any ambiguity it reports. Initialization does not build core or screens, run app builds or add code generators. If package setup cannot run, the agent reports the incomplete step.

### 2. Prepare the shared core when needed

To prepare the whole shared foundation up front, run:

```text
/flutter-core
```

The agent creates or completes routing, dependency injection, API/error handling, network services, localization, shared widgets, theme tokens/skins and app startup wiring. Existing working equivalents and package choices are preserved. If configuration is absent, it runs config-only `flutter-init` first and adds dependencies needed for core work.

You can also go straight to a screen, feature or theme implementation request. In a confirmed fresh app the agent prepares core automatically; in an existing app it fills only proven gaps needed for that task, preserving unrelated infrastructure and styles. A missing `lib/core` folder alone does not trigger setup when working equivalents exist elsewhere. The agent states its scope and continues without asking you to select skills. Core setup provides the foundation; provisional theme values are not a match to a design you have not supplied. Real backend integration still needs your API contract and endpoint configuration.

### 3. Apply the HTML design to the app theme

When you have the HTML design, run:

```text
/set-theme-from-html ./design/app.html
```

The agent resolves the design, prepares missing core through the scoped readiness workflow, imports its original icons, images and fonts, and applies the observed skin colors, spacing, radii, typography, elevation, motion and shapes through the existing theme and shared widgets. It verifies representative components and reports unsupported or unprovided values. This prepares foundations; it does not build business screens or replace working unrelated infrastructure.

Apply this step when preparing or deliberately refreshing app-wide foundations. An established app with the desired theme can go straight to screen work. If you do not have the design yet, continue using the existing theme and apply the design when it is available.

### 4. Build the screens you want

For one screen inside a whole-app HTML file:

```text
/html-to-widget ./design/app.html build the login screen
```

You can use an ordinary request instead:

```text
Build the login and signup screens from ./design/app.html.
```

Name the screens or feature you want implemented. The agent uses the existing core, selected packages and conventions, then captures Flutter output, compares supplied design states and reports measured differences. It also checks applicable behavior and regression variants, inspects candidate images, and runs ordinary golden tests after local baseline approval. States without a supplied design reference are reported separately from source-verified states. You do not need to select the verification skills yourself.

### 5. Update an already-working screen

When the HTML changes, update the design file and tell the agent:

```text
The login UI changed in ./design/app.html. Update the existing login screen.
```

The agent updates that implementation while preserving working validation, API calls, loading/error handling, controller ownership and navigation, then verifies it against the revised source. If the design path is already unambiguous in the conversation, you can simply say, "The login UI changed in the design. Update it." Supply the new path when you move or replace the design file.

For a deliberate app-wide foundation change, state that scope:

```text
The shared colors and fonts changed in ./design/app.html. Update the app theme
and verify the affected screens.
```

The agent selects the theme workflow for that request. A local screen update does not require repeating core setup or reapplying the whole theme. At handoff, check the source/Flutter/diff images, measured differences, behavior and golden results, and any remaining gaps. Missing source files or unavailable capture tooling are reported as blockers rather than successful verification.

## Project package configuration

Run `/flutter-init` in a Flutter project to create `flutter-knowledge.yaml`
from its `pubspec.yaml` and authored `lib/` source. It detects the existing stack and fills missing
categories using the skill package catalog. Existing selections are preserved;
ambiguous alternatives are reported with unresolved choices. The helper requires
Python 3.10+ and PyYAML (requirements are bundled with `flutter-init`). Config-only discovery records recommendations without installing packages; explicit empty-starter initialization has the dependency setup described above.

All task skills read the [configuration contract](plugins/flutter-knowledge/skills/flutter-init/references/configuration.md).
Source evidence also records shared widget/component locations, custom contract
entry points and asset declarations without creating a component inventory.
Package mechanics adapt while naming, layer ownership and other conventions
stay fixed. The renamed `flutter-state-management` skill keeps the existing
Cubit/state naming and uses Cubit for the default Bloc stack.

## Compatibility and evidence

The [configuration contract](plugins/flutter-knowledge/skills/flutter-init/references/configuration.md)
and [package adaptation](plugins/flutter-knowledge/skills/flutter-init/references/package-adaptation.md)
define compatibility: selected packages change implementation mechanics while
the architecture stays fixed. Feature/layer ownership, Screen/Body separation,
route-owned state provisioning, Cubit/state naming, owner-held data and
controllers, payload-free success states, model/params contracts, shared visual
tokens and complete English/Arabic translations still apply. Keep the
[generator restrictions](plugins/flutter-knowledge/skills/flutter-knowledge/SKILL.md#hard-rules-always-on).
The older-theme exception remains in its owning skill
notes; package selection does not broaden it.

Preserve working project contracts where the skills allow, follow explicit
user/project constraints, and keep changes within the requested scope. Conflicting
legacy patterns do not silently override the conventions or authorize unrelated
migrations. Report a precise incompatibility before dependent changes and continue
independent work. Catalog recognition supports detection; it does not verify every
package version or combination. Inspect installed APIs and relevant source for
the selected stack.

Local manifest and hook-contract checks establish repository wiring under their
test inputs; run `python3 tests/test_harness_compatibility.py` for those checks.
They do not establish live compatibility with all seven hosts or
reliable skill selection by their agents. The [state recipe fixture](tests/check_state_references.py)
checks specific package versions with host-side Flutter analysis/tests; those
results do not establish Android/iOS builds, native setup or device behavior.
The [agent benchmark](benchmark/README.md) measures its stated tasks and runs;
broader compatibility or token-reduction claims need separate evidence.
Use its [focused checks](benchmark/README.md#focused-discovery-and-compatibility-checks)
to select affected suites and compare skill discovery on identical requests.

## What's inside

| Skill | Purpose | Loads |
| --- | --- | --- |
| **flutter-init** | Detect packages and create or refresh flutter-knowledge.yaml; explicit empty-starter initialization also adds/resolves selected dependencies. | On request or config-only discovery before package-dependent work when config is absent |
| **flutter-core** | Create/complete the full foundation explicitly or in a fresh app; fill only task-required core gaps in existing apps, preserving working equivalents. | Explicit setup or automatic readiness during implementation; never read-only planning/review |
| **flutter-knowledge** | The map: always-on hard rules plus which skill to invoke before writing each kind of code. | Host hook/context loading or task-based discovery as described above |
| **flutter-feature-structure** | Feature folder tree, `_screen` suffix, the `lib/core/` folders, mirroring an existing equivalent file. | On demand, via `flutter-knowledge` or `/flutter-feature-structure` |
| **flutter-data-layer** | Models, params, remote data sources, repositories, `EndPoints`, `Failure`. | On demand, via `flutter-knowledge` or `/flutter-data-layer` |
| **flutter-state-management** | Cubit + state classes, per-method state naming, data and controller lifecycle. | On demand, via `flutter-knowledge` or `/flutter-state-management` |
| **flutter-screen-ui** | Screen/Body split, widget structure, core wrappers, design tokens through `context.tokens`, localization, navigation. | On demand, via `flutter-knowledge` or `/flutter-screen-ui` |
| **flutter-routing-di** | Routes in `lib/core/router/`, `BlocProvider` wiring, per-feature `get_it` injection files. | On demand, via `flutter-knowledge` or `/flutter-routing-di` |
| **drift-local-database** | Drift/SQLite local persistence: tables, DAOs, entities, migrations, local-only and hybrid repositories. | On demand, via `flutter-knowledge` or `/drift-local-database` |
| **hive-local-database** | Hive (hive_ce) local persistence: boxes, storage↔model mapping, local-only and hybrid repositories. | On demand, via `flutter-knowledge` or `/hive-local-database` |
| **flutter-testing** | Unit test conventions: mocktail mocks, bloc_test cubit tests, data source/repository/cubit coverage. | On demand, via `flutter-knowledge` or `/flutter-testing` |
| **add-translation** | Add localization key(s) to `en.json` and `ar.json` in sync, then regenerate `locale_keys.g.dart`. | On demand, via `flutter-knowledge` or `/add-translation` |
| **flutter-app-theme** | The `lib/core/theme` layer: `AppTokens` read as `context.tokens` (skin colors, spacing, radii, text, elevation, motion, shapes), skins as a list (built-in + JSON, `SkinRegistry`, `SkinCubit.select`), `AppTheme.of(skin)` with the `ColorScheme` mapping, when a design's value becomes a token, and `scripts/token_audit.py`, an audit that finds hardcoded values. | On demand, via `flutter-knowledge` or `/flutter-app-theme` |
| **flutter-accessibility-rtl** | Semantics, logical direction, large text, focus, targets and Arabic/RTL behavior. | Before affected user-facing UI work |
| **flutter-responsive-layout** | Parent constraints, breakpoints, overflow, keyboard/safe-area behavior and target sizes. | Before affected layout work |
| **flutter-performance** | Lazy lists, image decoding, rebuild/animation costs and evidence-based profiling. | When those mechanisms or performance concerns are touched |
| **flutter-review** | Read-only mechanical checks and manual architectural review, including app-relative untracked files. | Before substantial work is handed off, committed or reviewed |

## Design implementation and visual testing

Five skills cover the step between a design and the app, built on the
conventions above. The Figma, verification and golden skills were adapted from [Mohamed Draz's `flutter-design-fidelity`](https://github.com/draz26648/flutter_craft_skills)
(MIT). These design skills target projects on the current theme layer
(`context.tokens`).

| Skill | Purpose |
| --- | --- |
| **figma-to-widget** | Turns a Figma frame into widgets: Auto Layout to `Row`/`Column`, gaps to `VerticalSpace`, variables and styles to `context.tokens`, component instances to existing core widgets, `Stack` only where layers overlap. |
| **set-theme-from-html** | Applies the whole HTML design after automatic core readiness when needed: original assets/fonts, all seven theme groups and component mappings, with scoped source-backed checks. Invoke `/set-theme-from-html <html-design-path>` before later screen implementation. |
| **html-to-widget** | Turns an HTML prototype into widgets: reads the computed CSS with `scripts/layout-tree.js`, then maps flex to `Row`/`Column`, gaps to `VerticalSpace`, values to `context.tokens`, and JS-toggled states to cubit states. |
| **visual-verification** | Requires per-screen reference/Flutter/diff evidence and overall/worst-region percentages. Captures at matching viewport/DPR (default 750×1624), diffs them with `scripts/compare.py`, and fixes until it matches — four rounds of guesses, then only fixes whose cause is known. |
| **golden-tests** | Locks the matched screen in plain `flutter_test` goldens through a shared harness (the app's theme, real fonts and shadows), across the other skin, Arabic, 2× text and a small phone. |

These skills ship with `flutter-knowledge` on every supported harness.
They load from their descriptions or workflow handoffs; Gemini includes them
in its always-loaded context file.

## Install

Install separately for each harness you use. Every method reads the skills
straight from this repo (`plugins/flutter-knowledge/skills/`). All supported
harnesses receive the same 22 skills.

If you previously installed the separate `flutter-design-handoff` plugin, update
`flutter-knowledge` and remove the old plugin through your harness's plugin manager
to avoid loading duplicate skills.

### Claude Code

```bash
/plugin marketplace add OmarAly92/flutter-knowledge
/plugin install flutter-knowledge@flutter-skills
```

Update from a terminal — the first command refreshes the marketplace metadata, the second pulls the new version in:

```bash
claude plugin marketplace update flutter-skills
claude plugin update flutter-knowledge@flutter-skills
```

### Gemini CLI

```bash
gemini extensions install https://github.com/OmarAly92/flutter-knowledge
```

Update: `gemini extensions update flutter-knowledge`.

### OpenCode

Add to your `opencode.json`:

```json
{
  "plugin": ["flutter-knowledge@git+https://github.com/OmarAly92/flutter-knowledge.git"]
}
```

See [`.opencode/INSTALL.md`](./.opencode/INSTALL.md) for details. Update: `git pull` / clear the package cache.

### Pi

Install the package (its `package.json` exposes the Pi extension and skills):

```bash
pi package add github:OmarAly92/flutter-knowledge
```

### Codex

Run these in your OS terminal/shell — not inside an active Codex chat session
(that's where `/plugins` lives, for browsing what's already installed):

```bash
codex plugin marketplace add OmarAly92/flutter-knowledge
codex plugin add flutter-knowledge@flutter-skills
```

Then start a new Codex session to pick up the plugin. It reads
`plugins/flutter-knowledge/.codex-plugin/plugin.json`, which registers that
plugin's `skills/` and — like Claude
Code — wires up the `SessionStart` hook that force-loads `flutter-knowledge`
for Flutter projects.

Update: run both of these — the first refreshes the marketplace snapshot, the second reinstalls the latest version.

```bash
codex plugin marketplace upgrade flutter-skills
codex plugin add flutter-knowledge@flutter-skills
```

### Cursor / Kimi

Add this repo through the harness's plugin/extension manager. Each reads its own
manifest — `.cursor-plugin/plugin.json`, `.kimi-plugin/plugin.json` — which
registers `./plugins/flutter-knowledge/skills/`. Unlike Codex, these two are description-based triggering
only; no hook is wired up.

### Any other agent (universal fallback)

For any agent that reads `SKILL.md` files from `~/.claude/skills/`:

```bash
git clone https://github.com/OmarAly92/flutter-knowledge.git
cd flutter-knowledge
./install.sh
```

This symlinks all 22 skills into `~/.claude/skills/`, skipping any name that already exists there as a real folder (override the target with
`CLAUDE_SKILLS_DIR=/path ./install.sh`). Update with `git pull` and re-run
`./install.sh`.

## Repo structure

The plugin lives in `plugins/flutter-knowledge/` with Claude Code and Codex
manifests and one `skills/` folder. Every harness points at this folder.
See [`CONTRIBUTING.md`](./CONTRIBUTING.md) for the full map and how to add a
skill or cut a release.

## License

MIT — see [`LICENSE`](./LICENSE). The plugin's
[`LICENSE`](./plugins/flutter-knowledge/LICENSE) preserves Mohamed Draz's
copyright for the adapted design skills.

## Checking changes to the skill implementation

Run `python3 tests/test_flutter_init.py`, `python3 tests/test_flutter_review.py`,
`python3 tests/test_token_audit.py` and `python3 tests/test_compare.py` for helper changes.
The state recipes are assembled from their reference code into an isolated temporary
Flutter fixture by `python3 tests/check_state_references.py`; use
`--riverpod-version 2.6.1` to exercise the older checked API. Resolution is offline by
default; `--fetch` explicitly permits dependency downloads for that fixture. The
fixture requires Dart 3.9+ and never writes code into an application checkout.
Run the full agent benchmark before integration as described in `benchmark/README.md`.

Single-screen design requests build immediately and verify against the original HTML/Figma reference. Whole-app design planning produces foundation and per-screen briefs; explicit implementation continues through them. Every implemented design-backed screen/state gets its own comparison report, including overall pixel difference, worst-region difference and artifact links. Missing references or capture blockers are reported as not verified. See the [completion contract](plugins/flutter-knowledge/skills/visual-verification/SKILL.md#required-completion-contract).

Task routing and completion are defined once in [task workflows](plugins/flutter-knowledge/skills/flutter-knowledge/references/workflows.md). Source inspection belongs to HTML/Figma readers; conventions to implementation skills; comparison to visual verification; capture/regression to golden tests; and findings to review.

The workflow reuses source facts/references only after dependency/profile/renderer fingerprint checks, resolves source-versus-token decisions early, retains full logs with concise summaries, and batches final checks. Required comparisons, variant inspection and review remain unchanged. See [cache safety](plugins/flutter-knowledge/skills/visual-verification/references/design-cache.md).

Before a design capture matrix, [calibration](plugins/flutter-knowledge/skills/visual-verification/references/preflight.md#reusable-component-calibration) checks effective typography, layout-versus-crop scaling, painted field bounds and shared composition through the real core/camera. Matching inspected inputs can reuse that scoped calibration; they never verify current screens.

[State coverage and baseline handoff](plugins/flutter-knowledge/skills/golden-tests/references/coverage-handoff.md) keep supplied design comparisons separate from unprovided-state regression/behavior checks. Inspected eligible candidates are promoted with prior PNG/profile/review backups, checked by ordinary golden tests without updating, and recovered through a resumable transaction if interrupted or rejected. Declared coverage does not prove that unvisited states were discovered.

[Stage measurements](plugins/flutter-knowledge/skills/visual-verification/references/stage-usage.md) record local timings/command counts and available provider counters without estimating missing tokens. Workload-matched comparisons preserve required coverage; these helpers do not promise a percentage reduction or establish provider billing. These steps are selected by the agent during authorized design work, without new user commands.
