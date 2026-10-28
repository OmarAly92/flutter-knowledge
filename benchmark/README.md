# Skill benchmark

Measures whether agents follow the skills in this repo, so a skill change can be checked against `master` before it ships.

GitHub Actions runs focused deterministic checks for changed helpers, dependency manifests, skill catalogs and harness integrations on two runtime pairs: Python 3.10 with Node 22, and Python 3.14 with Node 24. Preview selection with `python3 scripts/focused_checks.py --base master --dry-run --json`, run it without `--dry-run`, or use `--files <paths...>` / `--all`. Unknown scripts and CI/dependency changes select the full deterministic set; unrelated documentation selects no checks. Browser suites require installed Chrome and Playwright; CI installs the Playwright adapter only when selected. Required-runtime skips fail the job. These checks do not run model agents, the implementation benchmark, live harness clients, native apps or Flutter/Dart recipe tests, and do not download Flutter. Changed state recipe references are reported under `required_manual_checks` for separate Flutter analysis and execution. The paired discovery probe and applicable implementation benchmarks below remain separate release evidence.

Each run gives one agent a realistic Flutter project and one task. A static grader then counts which conventions the agent broke. Every project is in the 2.0.0 shape the skills teach: design tokens read as `context.tokens` from `lib/core/theme/` (`AppSkin` with `LightSkin`/`DarkSkin`, `AppSpacing`, `AppRadius`, `AppTypography`, `AppElevation`, `AppTheme`), a data core in `lib/core/data/` (`ApiConsumer`, `GlobalResponse`, `Failure`/`Result`), `NetworkStatus` in `lib/core/services/`, `LocaleKeys` in `lib/core/l10n/`, the router library in `lib/core/router/`, the global `sl` in `lib/core/di/injection.dart`, one `<feature>_injection.dart` per feature wired through `lib/app_injection.dart`, a `test/app_injection_test.dart`, and core widgets grouped by role under `lib/core/widgets/`. Each project also contains legacy code that breaks the rules on purpose: `RoutesStrings._()`, an `orders` feature on Bloc whose injection file registers untyped `sl()` lookups, and (drift) a `budget` feature whose params return a drift `Companion` and whose data source core DI registers untyped. An agent that copies the code around it instead of following the skills gets caught.

The newer tasks (f1, f2, t1, g1) run on a third project, `app`: the drift project plus a `trips` feature written the way the skills ask, shared email and phone validators, a legacy flat `test/` file that uses mockito, and a design prototype at `design/prototype.html`. The prototype is built like a standalone design export: its real CSS sits escaped inside a JS string, the page's own `<style>` holds a decoy `--primary`, and its font is embedded as compressed base64. Reading the file by eye gives the wrong values, so it tests whether an agent follows the design skill's extraction steps. Task m2 also runs here: `app` has no `AppMotion`, but the prototype defines motion tokens, so it checks that an agent creates one with documented tokens whose values come from the prototype, and adds it to `AppTokens` as the `motion` group.

Tasks s1, s2 and m1 run on a fourth project, `skin`: the `app` project with skins as a list (`SkinRegistry` holding the built-ins plus `assets/skins/ocean.json`, a `JsonSkin` with its parser, `SkinCubit.select` persisted through `CacheHelper`, `MaterialApp(theme: AppTheme.of(skin))`), plus an `AppMotion` token group with durations, curves, stagger helpers and `motor` springs. s1 and s2 check the skin part of the `flutter-app-theme` skill: colors come from `tokens.skin`, a new color becomes a documented slot implemented in both built-in skins and registered for JSON skins (the slot name lists, `JsonSkin`, every `assets/skins/*.json`), and the mode switch goes through `SkinCubit`. m1 checks its motion part: animation durations, curves, springs and stagger delays come from `tokens.motion`, and a new timing becomes a documented token there. The legacy `orders` feature still uses raw colors, as a trap.

Task o1 runs on a fifth project, `older`: the `app` project on the pre-2.0 theme (a flat `AppColors` and a static `AppTextStyle` under `lib/core/app_themes/`, no `AppTokens`). It is f1 again, and checks the skills' older-project notes: the agent keeps the project's own theme classes and does not migrate it to `context.tokens` on the side.

**The fixtures were ported to the 2.0.0 shape after the rounds below.** Those rounds ran on the pre-2.0 fixtures and grader (`lib/core/app_themes/`, `AppColors`/`context.skin`, `service_locator.dart` with `_xFeatureSetup`), so their numbers are not comparable with runs on the current fixtures. Run master and the branch on the same fixtures, as `prepare.py` does.

## Results so far (Sonnet 5.5, 2026-09-28)

These are the same 20 runs per version: 5 screen tasks, with 3 forced runs and 1 description-only run each.

| | 1.2.1 (single skill) | 1.3.0 split (PR #1) | 1.3.0 + translation fix (PR #2) |
|---|---|---|---|
| Rule breaks | 30 | 13 | 2 |
| Runs using a translation key missing from the JSON | 15 | 7 | 0 |
| Runs with real Arabic for new keys | 0 | 1 | 20 |
| Mean tokens per run | 117.7k | 124.0k | 123.5k |

### Newer tasks, master baseline (1.3.0, 2026-09-28)

Each task ran 3 times in forced mode and once in description-only mode, 16 runs in all.

| Task | Runs | Rule breaks | Mean skill files read | Mean tokens |
|---|---|---|---|---|
| f1 trip details + delete sheet | 4 | 0 | 7.0 | 108.4k |
| f2 edit form | 4 | 0 | 7.0 | 100.7k |
| t1 unit tests | 4 | 0 | 2.8 | 85.8k |
| g1 design prototype | 4 | 0 | 4.0 | 133.7k |

Master broke no rule on these tasks either. Every g1 run ignored the decoy color, pulled the real values from the rendered CSS, and extracted both embedded fonts. In description-only mode the agents still found `flutter-testing` for t1 and `design-from-html-flutter` with its playbook for g1. These tasks are a regression baseline: a skill change should keep them at 0.

### 1.3.1: flutter-testing cubit example fix (2026-09-28)

The skill's cubit example expected the constructor fetch's loading state, which `blocTest` never records because it subscribes after `build()` returns. Every master t1 run noticed and wrote around it. On 1.3.1, t1 again broke no rule in 4 runs (forced ×3, desc ×1), the agents used the example's `act:` and `skip:` pattern directly, and mean tokens fell from 85.8k to 73.7k. The grader now flags a `blocTest` that expects that loading state (`cubit_test_expects_ctor_loading_state`).

### 1.4.0: flutter-app-skin (2026-09-29)

New tasks s1 and s2 on the `skin` project, forced ×3 and desc ×1 each, plus f1 forced ×2 as a regression check on an `AppColors` project. 10 runs per version.

| | master (1.3.1) | 1.4.0 |
|---|---|---|
| Rule breaks | 5 | 0 |
| Runs with an s2 tint hand-picked per skin instead of derived | 4/4 | 0/4 |
| Runs adding skin slots without a doc comment | 1/10 | 0/10 |
| Runs reading `flutter-app-skin` on s1/s2 | - | 8/8 (desc mode too) |
| Mean tokens | 91.4k | 98.9k |

Permutation test p = 0.03. Master agents already used `context.skin`, never `AppColors`, and switched the mode through `SkinCubit`, because the fixture's own code shows the pattern. The difference is in how they add colors: on 1.4.0 every run made the gold's soft tint a derived slot (`premium.withValues(alpha: 0.16)`), while every master run added a second abstract slot and invented a light-mode value for it. `s2_tint_not_derived` was added after reading these runs, so treat it as a finding to confirm on the next round, not a pre-registered test. f1 broke no rule on either version, and its agents did not read the skin skill.

### 1.5.0: flutter-app-theme (2026-09-29)

`flutter-app-skin` became `flutter-app-theme`, which keeps the skin rules and adds text styles, motion, shapes and `ThemeData`. Round 1 ran m1 (forced ×3, desc ×1), s1, s2 ×2 and f1 in forced mode, 8 runs per version. Round 2 ran m2 (forced ×3, desc ×1) per version.

| | master (1.4.0) | 1.5.0 |
|---|---|---|
| m2 rule breaks (4 runs each) | 6 | 0 |
| m2 runs creating `AppMotion` tokens without doc comments | 4/4 | 0/4 |
| m2 runs whose motion values are not the prototype's | 1/4 | 0/4 |
| m1, s1, s2, f1 rule breaks (8 runs each) | 1 | 0 |
| Mean tokens, m2 | 112.5k | 133.2k |
| Mean tokens, m1, s1, s2, f1 | 116.5k | 115.5k |

Permutation test on m2: p = 0.03. Every master m2 run created an `app_motion.dart` of 13 to 15 tokens with no doc comments, while every 1.5.0 run documented each token. The first 1.5.0 m2 round copied the skill's reference numbers instead of the prototype's in 2 of 3 forced runs, so the skill now says motion values come from the project's design and uses the reference set only when there is none. The 4 m2 runs above are the rerun after that fix, and all of them used the prototype's 120 and 360 ms, both cubic-beziers, the 12 px offset, the 0.97 press scale and the 60 ms stagger. `m2_motion_not_from_design` was added after reading the first round, so treat it as a finding to confirm on the next round, not a pre-registered test.

m1 is saturated. The fixture's documented `AppMotion` guides master agents too, so neither version broke a motion rule there; it is a regression check, like f1. Every 1.5.0 run on m1, s1 and s2 read `flutter-app-theme` (desc mode too), and f1 did not. On m2, 1.5.0 used 18% more tokens: its agents read more skill files (5.5 vs 3.8) and the theme skill is about 70% larger than the skin skill (31 KB vs 18 KB).

Grader fixes from reading these runs: `created_new_wrapper` ignores effect widgets in `lib/core/widgets/animation/`, `multiple_widgets_per_file` no longer counts `State` classes, an animated leaf widget may be stateful on m1 and m2, and a `SizedBox` with both a width and a height is a size, not a spacer.

### 2.5.0: one plugin, core/init/theme skills (2026-10-13)

The full default plan, 48 runs per version on Sonnet 5.5: master (2.1.0) against the branch before the routing fix (v250).

| | master | v250 |
|---|---|---|
| Rule breaks | 34 | 37 |
| Runs editing legacy orders code | 1 | 24 |
| Other rule breaks | 33 | 13 |
| Runs hand-editing `locale_keys.g.dart` | 18 | 10 |
| Mean skill files read | 6.7 | 8.0 |
| Mean tokens | 83.1k | 99.7k |

Permutation test p = 0.79. Almost all of v250's extra breaks came from one sentence in `flutter-routing-di`: "registration functions take no container parameter" led agents to rewrite the project's existing app, core and orders registration functions. The skill now keeps existing signatures and has new features use global `sl`. A first wording (v251) overcorrected, and 6/10 runs kept `RoutesStrings._()` in files they edited, so the exception now names only the registration signatures. On forced d1, d2, d3, h1 and h2 ×2:

| | master | v250 | v251 | v252 (shipped) |
|---|---|---|---|---|
| Rule breaks (10 runs) | 7 | 12 | 13 | 4 |
| Runs editing legacy orders code | 0 | 9 | 1 | 1 |
| Mean tokens | 91.5k | 109.8k | 107.2k | 110.0k |

Grader fixes from reading these runs: an argument-free `registerXDependencies()` call counts as wired, g1 accepts `set-theme-from-html` as the task skill, and the d4 checks find the budget files wherever the agent moved them.

### Placement, nav bar recipe and design-only screens (2026-10-28)

New tasks n1, p1 and u1 on the `app` project, forced ×3 and desc ×1 each, plus f1 and f2 forced ×2 as a regression check: 16 runs per version, Sonnet 5.5, run 4 at a time. The branch adds the `presentation/widget/` and `logic/helpers/` placement rules, the app nav bar recipe and the design-only screen rule.

| | master | branch |
|---|---|---|
| Rule breaks (16 runs) | 26 | 10 |
| n1 runs not following the nav bar recipe's files | 4/4 | 0/4 |
| p1 runs importing the shared row from another screen's `ui/widgets/` | 4/4 | 0/4 |
| u1 runs putting the design's sample content in the translation files | 4/4 | 0/4 |
| Mean skill files read | 7.7 | 7.2 |
| Mean tokens | 123.8k | 122.1k |

Permutation test p = 0.01. Every branch n1 run built `app_nav_bar` with the recipe's eight files, an `IndexedStack` and one `MultiBlocProvider` route; master runs named it `main_nav` or `main`, and one used no `IndexedStack`. Every branch p1 run moved `TripItem` to `trips/presentation/widget/`. No u1 run on either version built a fake data layer, because the task says there is no API; the difference is that master put the four rows' text in `en.json`/`ar.json` while the branch kept it as literals in the widgets. f1 and f2 broke no new rule. Hand edits of `locale_keys.g.dart` (1 vs 6) are within the earlier rounds' rate and unrelated to the change. `n1_recipe_files_missing` measures sameness to the recipe, so master cannot pass it without the recipe.

Grader fixes from reading these runs: the nav bar's `ChangeTabSuccessState(tab)` and its listener-free shell screen are sanctioned, and translation groups for features the run created are allowed.

Round 2 tightened the four rules behind the branch's remaining breaks: never hand-edit `locale_keys.g.dart`, no number literal (`0` included) in spacing, translation groups per feature folder, and `AppTextField.textInputAction` required (added to the wrapper when missing). It also made the design-only rule cover requested or supplied sample data, and added task u2: the u1 screen with "use the mockup's sample notifications as mock data" and no mention of an API. The grader gained `text_field_without_textInputAction`, `text_input_action_not_required` and `u1_sample_data_file`. Forced ×2 on n1, p1, u1, u2, f1, f2 for the new version (branch2) and u2 ×2 for master:

| | master | branch | branch2 |
|---|---|---|---|
| Rule breaks per run, on the cells each pair shares | 2.13 (15 runs) | 0.85 (13 runs) | 0.00 (12 runs) |
| u2 runs building a fake data layer or sample-data objects | 2/2 | - | 0/2 |
| f2 runs leaving `textInputAction` optional or unpassed | 2/2 | 1/2 | 0/2 |
| Runs hand-editing `locale_keys.g.dart` | - | 5/13 | 0/10 |
| Mean tokens | 124.0k | 123.8k | 125.5k |

master vs branch2 p < 0.001; branch vs branch2 p = 0.002. Both master u2 runs reproduced the failure: one built `NotificationModel`, a mock data source, a repository and a cubit; the other filled sample records into cubit lists. Every branch2 u2 run wrote the four rows as literals in `NotificationsBody`, with no cubit or DI.

Regression check on the tasks these rounds did not touch (d1, d2, h1, t1, g1, o1, forced ×2 per version, 4 agents at a time): master broke 5 rules in 12 runs (one d1 run skipped the schema bump and migration; both h1 runs hand-edited `locale_keys.g.dart`), branch2 broke none in 12. Every branch2 d1 run still built the drift table, DAO, local data source and repository, so the design-only rule did not leak into local-only features. Mean tokens 140.6k vs 148.7k, mostly from longer g1 runs. Grader fixes from reading these runs: the hybrid check accepts `GlobalResponse<T>(...)`, and a Hive box call inside a private helper counts as guarded when the helper's call is wrapped in `handleLocalFailure`. Across every cell the two versions share, master breaks 1.37 rules per run (27 runs) and branch2 0.00 (24 runs).

### Description discovery: scoped Codex comparison

The pre-change working-tree catalog and shortened catalog were tested on the
same [48 requests](selection_cases.json), with five fresh Codex/gpt-6.1-sol
high-reasoning agents per variant. Both selected the expected entry skill on
240/240 decisions. Descriptions shrank from 1,185 to 491 words and from 8,728 to
3,937 UTF-8 bytes. All 22 skill bodies and 51 supporting resources were unchanged
against that snapshot. The baseline included earlier uncommitted init/core work;
it was not committed `master` or the historical Sonnet benchmark.

Eight local harness tests, six selection-grader tests and 127 focused helper
tests passed on Python 3.14.0 / Node 25.9.0 on macOS. Six independent workflow
probes checked alternative packages, legacy themes, existing generation,
architectural conflicts, read-only review and unavailable-tool handling; these
were instruction-route checks, not Flutter execution. The saturated discovery
sample establishes no observed regression on those requests, not general trigger
reliability, live-host certification or end-to-end token savings. Raw local
artifacts are in ignored `benchmark/out/discovery-compat-20261017/`.

### Fresh-project automatic core and handoff smoke

One real empty Flutter starter received an ordinary request for a localized
profile-name settings screen, without naming specialists. The consumer selected
configuration discovery, full fresh-core setup and the implementation/test/review
owners. Independent review found and corrected failed-preference cache recovery,
nested form-log redaction, component skin-role mapping and iOS locale metadata.
The final uninterrupted host gate passed 23 tests, fatal-info analysis and
formatting; a read-only readiness assessment preserved all 153 frozen files and
found no duplicate setup. It was not a second blind implementation run.

Android and targeted arm64 iOS storage-probe builds/installations passed, but
launch markers were not observed; native storage runtime and the main app's
native UI remain unverified. An interrupted run also exposed a zero-exit test
failure reporting bug: the review helper now blocks recognized failing reporter
output despite exit code 0, with passing-marker and failure regressions tested
on Python 3.10 and 3.14. Raw evidence is retained in ignored
`benchmark/out/ci-fresh-flow-20261018/`; provider token counters are unavailable.

### Tested core references: scoped validation

The cache, Dio/Talker logger and Material mapping references pass 47 host
contract/widget tests plus a compiled product-mode logger probe on Flutter
3.44.5/Dart 3.12.2. Fixture pins record the exercised package versions rather
than application dependency requirements. A paired, blind cache-only task had
both submitted implementations pass the same 25 public-contract checks; each
preserved seven original caller/key/config/dependency files. The candidate used
the matching cache references unchanged and did not load unrelated logger/theme
implementations. This proves scoped adoption/preservation on that sample, not
fewer general errors, statistical improvement or token savings. Initial stricter
scores reflected private policy differences and are retained as diagnostics.
Local raw evidence is in ignored `benchmark/out/core-references-20261018/`.

## Files

| File | What it is |
|---|---|
| `build_fixtures.py` | Writes the drift, Hive, `app`, `skin` and `older` fixture projects, plus a `-nowrap` copy of each with `PrimaryButton`, `AppTextField`, `AppLoader` and `AppErrorWidget` removed. |
| `fixture_files/design/prototype.html` | The design prototype copied into the `app` fixture for task g1. |
| `make_prototype.py` | Regenerates that prototype and its embedded font. It needs `fonttools`, and you only run it to change the prototype. |
| `tasks.json` | The two agent prompt templates, the three modes, the tasks, and the default plan. |
| `prepare.py` | Builds the fixtures, makes one project copy per run, writes a skill index per version, and writes one prompt per run to `out/agents.jsonl`. |
| `grade.py` | The grader. It runs regex checks on the code each agent wrote and writes `out/grades.json`. |
| `compare.py` | Compares versions on the tasks they all ran. It prints rule breaks, translation outcomes, tokens and skill files read, and runs a permutation test. |

Generated output goes to `benchmark/out/`, which git ignores.

The grader requires PyYAML. Unit-test mocking checks follow `packages.mocking`
when a configuration exists and check the dependencies actually imported by new
tests. Mockito is permitted when selected; an undeclared import or a mismatch
with the configured mechanism remains a violation. Historical results using the
former unconditional Mockito check are not directly comparable with this rule.

### Tasks

| Task | Storage | What the agent builds |
|---|---|---|
| d1 | drift | A local-only notes screen |
| d2 | drift | A products list cached for offline use |
| d3 | drift | Offline-first tasks with a sync job |
| d4 | drift | An optional column on the shipped `budget` table, with a migration (data side only) |
| h1 | Hive | Same as d2 |
| h2 | Hive | Same as d3 |
| f1 | app | A trip details screen loaded by id, with a delete confirmation in a bottom sheet |
| f2 | app | An edit trip screen with a prefilled, validated form that saves by id |
| t1 | app | Unit tests for the existing trips data source, repository and cubit |
| g1 | app | Colors, font, text styles, motion and two core widgets taken from the HTML prototype |
| s1 | skin | A status pill on each trip that works in light and dark mode, plus an app bar button that switches the mode |
| s2 | skin | A "Premium" label in a new gold color that differs between light and dark mode |
| m1 | skin | A staggered entrance for the trips list, a press that shrinks each card and springs back, and a slowly pulsing dot on upcoming trips |
| m2 | app | The same as m1, on a project with no `AppMotion` yet |
| o1 | older | f1 on a project that predates `context.tokens` |
| n1 | app | A bottom nav bar as the main screen, with the trips list and a new profile screen as tabs |
| p1 | app | A trip summary screen that reuses the trips list's row and totals the trips |
| u1 | app | A notifications screen from a design with no API yet |
| u2 | app | u1 with "use the sample notifications as mock data" and no mention of an API |

f1 and f2 cover what the first six tasks never reach: `EndPoints` methods that take an id, `registerFactoryParam` with `param1`, a bottom sheet given the cubit through `BlocProvider.value`, controllers and the form key on the cubit, prefilling through the initializer list, `dispose` in `close()`, and the shared validators. t1 checks `flutter-testing`; g1 checks `html-to-widget` and its source-extraction reference. The grader also accepts the former design skill/playbook for historical master baselines, so removing the old entry point does not penalize historical runs.

### Modes

| Mode | Simulates |
|---|---|
| `forced` | Claude Code, Codex, OpenCode and Pi, which inject the `flutter-knowledge` map up front |
| `desc` | Cursor, Kimi and `install.sh`, where the agent sees only skill descriptions |
| `nowrap` | Forced mode on the project with four core widgets missing |

The default plan is forced ×3 and desc ×1 on d1–d4, h1, h2, f1, f2, t1, g1 and o1, plus nowrap ×2 on d1 and h1. That is 48 runs per version. To run only the newer tasks, use `--only forced:f1,f2,t1,g1:3 --only desc:f1,f2,t1,g1:1`.

## Running it

### Focused discovery and compatibility checks

Description changes can first use the smaller, description-only probe:

```sh
python3 benchmark/skill_selection.py prepare --root ../fk-master --out benchmark/out/selection/before
python3 benchmark/skill_selection.py prepare --root . --out benchmark/out/selection/after
```

Freeze both source trees before preparing. Each output contains a catalog, body
hashes and the same 48 requests in `prompt.txt`, without expected answers. Give
only that prompt to a fresh agent per repetition and save its JSON decisions.
Use the same provider, model and reasoning settings for both variants, with five
independent repetitions each; record those settings with the results. Do not load
the map or skill bodies in this probe, since it measures description discovery.
Resume from saved result files after interruption instead of rerunning completed
samples. Keep any exploratory or revised-catalog results separate.

```sh
python3 benchmark/skill_selection.py score --before benchmark/out/selection/before --after benchmark/out/selection/after --result before=benchmark/out/selection/before-1.json --result after=benchmark/out/selection/after-1.json
```

Repeat `--result before=... --result after=...` for every paired repetition. The
grader rejects missing/unknown decisions, changed request fixtures, duplicate
result paths and unequal repetition counts. It reports exact routing accuracy,
case regressions, description words/bytes and changed skill-body hashes. Inspect
every miss; a routing pass does not establish implementation quality or total
token savings. For a working-tree comparison, freeze the live pre-change tree
and label it as such instead of calling it `master`. Historical Sonnet results
above are not comparable to runs on another model.

Run the focused checks for the surfaces actually changed:

| Changed surface | Local checks |
| --- | --- |
| Descriptions or discovery benchmark | `python3 tests/test_skill_selection.py`, paired agent probe above, skill frontmatter validation |
| Harness manifests, hooks, installer or Gemini includes | `python3 tests/test_harness_compatibility.py` |
| Package detection/configuration or empty-starter setup | `python3 tests/test_flutter_init.py` and `python3 tests/test_flutter_init_bootstrap.py` |
| Core inspection or findings-only review | `python3 tests/test_flutter_core.py` and `python3 tests/test_flutter_review.py` |
| Core reference implementations, theme fragments or pinned fixtures | `python3 tests/test_core_references.py` for packaging/reporting, then `python3 tests/check_core_references.py` (or `--only cache`, `--only logger`, `--only theme`) with Flutter/Dart; offline by default, `--fetch` permits fixture dependencies |
| State-package recipes or their dependency versions | `python3 tests/check_state_references.py` with the resolved APIs; inspect its flags before selecting backends |
| HTML extraction, foundations or assets | `python3 tests/test_layout_tree.py` and `python3 tests/test_html_to_theme.py` |
| Reference reuse, comparison or regression handoff | `python3 tests/test_design_cache.py`, `python3 tests/test_compare.py` and `python3 tests/test_golden_handoff.py` |

Harness checks execute real hook/extension files with temporary projects and
host-shaped callbacks; manifests and Gemini includes get structural checks.
They do not launch or certify the seven host clients. Node is needed for hook
execution and native TypeScript support for Pi execution; unavailable runtimes
are explicit skips, not passes for those integrations. Package/native behavior
still requires checks against the installed Flutter/package versions and the
affected target platform. These focused checks supplement the implementation
benchmark; use its relevant task slice when skill instructions or recipes change.

Core reference edits select the Python packaging/reporting suite and explicitly
report required Flutter followup. Python/Node CI does not compile those Dart
assets or satisfy that check. The Flutter runner copies the shipped sources into
an isolated fixture, formats only that workspace, exercises the host contracts
and widgets, and compiles the logger's product-mode smoke probe. It neither
overwrites an existing app nor verifies native storage or a target design.

### Full implementation benchmark

Use **Sonnet 5.5 (`claude-sonnet-5-5`)** for every agent, so results stay comparable with the table above. In Claude Code the steps are:

1. Check out each version side by side, and don't edit them while the benchmark runs:
   ```sh
   git worktree add ../fk-master master
   git worktree add ../fk-mybranch my-branch
   ```
2. Prepare the runs from the repo root:
   ```sh
   python3 benchmark/prepare.py --version master=../fk-master --version mybranch=../fk-mybranch
   ```
   Version names can't contain `-`. Add `--only forced:d1,d2:3` to run a slice instead of the default plan (repeat it for more slices).
3. Launch one subagent per line of `benchmark/out/agents.jsonl`. Each gets exactly the `prompt` on that line, runs in the background with its own context, and uses Sonnet 5.5. Claude Code runs at most 20 subagents at a time, so start the next one as each finishes. When a subagent finishes, append `<run> <tokens>` to `benchmark/out/tokens.txt`.
4. Grade the runs, then read the code behind every rule hit. The checks are regexes, so they can misfire. Fix any false positive in `grade.py` and grade again.
   ```sh
   python3 benchmark/grade.py benchmark/out
   ```
5. Compare the versions:
   ```sh
   python3 benchmark/compare.py benchmark/out --versions master,mybranch
   ```

### Rerun prompt

Paste this into Claude Code at the repo root, replacing `<branch>` and `<name>`:

> Run the flutter-knowledge benchmark comparing master with `<branch>`, following benchmark/README.md. Create worktrees ../fk-master and ../fk-`<name>`, and don't change either checkout. Run `python3 benchmark/prepare.py --version master=../fk-master --version <name>=../fk-<name>`. For every line of benchmark/out/agents.jsonl, launch one background general-purpose subagent on Sonnet 5.5 (claude-sonnet-5-5) with exactly that prompt, keeping at most 20 running at once. As each one finishes, append "<run> <subagent tokens>" to benchmark/out/tokens.txt. When all have finished, run benchmark/grade.py and read the code behind every rule hit. Fix false positives in benchmark/grade.py and say what you changed. Then run `benchmark/compare.py benchmark/out --versions master,<name>`. Report rule breaks per run and the p-value, the rules that differ, translation outcomes, tokens and skill files read, and anything you noticed that the grader can't see.

## Reading the results

- **Rule breaks** counts, for each run, how many distinct rules it broke, summed over runs. Rule names in the output match the checks in `grade.py`. Most rules are broken by no one; the useful signal is in the few that differ between versions.
- **Compare only the same cells.** `compare.py` does this for you. Don't compare one version's d4 or nowrap runs with another version that skipped them.
- **Small cells are noisy.** Description-only mode has one run per task, and a single run can flip a cell. Trust the p-value over one cell.
- **Translation outcomes** are reported separately. "Real Arabic" means the new keys in `ar.json` contain Arabic script.

## Changing the benchmark

- **New task:** add it to `tasks.json`. If it needs new code in the fixture project, change `build_fixtures.py`, and add checks for it in `grade.py`.
- **New rule:** add a check in `grade.py` next to the related ones, grade old runs again, and read every new hit before trusting it.
- **Rebuilding fixtures:** delete `benchmark/out/fixture-*` so `prepare.py` rebuilds them. Results from different fixtures aren't comparable.
