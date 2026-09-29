# Skill benchmark

Measures whether agents follow the skills in this repo, so a skill change can be checked against `master` before it ships.

Each run gives one agent a realistic Flutter project and one task. A static grader then counts which conventions the agent broke. The project has a real core layer (`ApiConsumer`, `GlobalResponse`, `NetworkStatus`, `Failure`/`Result`, `AppColors`, `AppTextStyle`, `LocaleKeys`, core widgets). It also contains legacy code that breaks the rules on purpose: `RoutesStrings._()`, an `orders` feature on Bloc with inline DI, and a `budget` feature whose params return a drift `Companion`. An agent that copies the code around it instead of following the skills gets caught.

The newer tasks (f1, f2, t1, g1) run on a third project, `app`: the drift project plus a `trips` feature written the way the skills ask, shared email and phone validators, a legacy flat `test/` file that uses mockito, and a design prototype at `design/prototype.html`. The prototype is built like a standalone design export: its real CSS sits escaped inside a JS string, the page's own `<style>` holds a decoy `--primary`, and its font is embedded as compressed base64. Reading the file by eye gives the wrong values, so it tests whether an agent follows the design skill's extraction steps.

Tasks s1 and s2 run on a fourth project, `skin`: the `app` project with `AppColors` replaced by an `AppSkin` layer (`LightSkin`/`DarkSkin`, `SkinScope` and `context.skin`, `SkinCubit` persisted through `CacheHelper`, `AppThemes.fromSkin`). They check the `flutter-app-skin` skill: colors come from `context.skin`, a new color becomes a documented slot implemented in both skins, and the mode switch goes through `SkinCubit`. The legacy `orders` feature still uses raw colors, as a trap.

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

## Files

| File | What it is |
|---|---|
| `build_fixtures.py` | Writes the drift, Hive and `app` fixture projects, plus a `-nowrap` copy of each with `PrimaryButton`, `AppTextField`, `AppLoader` and `AppErrorWidget` removed. |
| `fixture_files/design/prototype.html` | The design prototype copied into the `app` fixture for task g1. |
| `make_prototype.py` | Regenerates that prototype and its embedded font. It needs `fonttools`, and you only run it to change the prototype. |
| `tasks.json` | The two agent prompt templates, the three modes, the ten tasks, and the default plan. |
| `prepare.py` | Builds the fixtures, makes one project copy per run, writes a skill index per version, and writes one prompt per run to `out/agents.jsonl`. |
| `grade.py` | The grader. It runs regex checks on the code each agent wrote and writes `out/grades.json`. |
| `compare.py` | Compares versions on the tasks they all ran. It prints rule breaks, translation outcomes, tokens and skill files read, and runs a permutation test. |

Generated output goes to `benchmark/out/`, which git ignores.

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

f1 and f2 cover what the first six tasks never reach: `EndPoints` methods that take an id, `registerFactoryParam` with `param1`, a bottom sheet given the cubit through `BlocProvider.value`, controllers and the form key on the cubit, prefilling through the initializer list, `dispose` in `close()`, and the shared validators. t1 checks the `flutter-testing` skill and g1 the `design-from-html-flutter` skill, including whether an agent in description-only mode reads them at all.

### Modes

| Mode | Simulates |
|---|---|
| `forced` | Claude Code, Codex, OpenCode and Pi, which inject the `flutter-knowledge` map up front |
| `desc` | Cursor, Kimi and `install.sh`, where the agent sees only skill descriptions |
| `nowrap` | Forced mode on the project with four core widgets missing |

The default plan is forced ×3 and desc ×1 on all ten tasks, plus nowrap ×2 on d1 and h1. That is 44 runs per version. To run only the newer tasks, use `--only forced:f1,f2,t1,g1:3 --only desc:f1,f2,t1,g1:1`.

## Running it

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
