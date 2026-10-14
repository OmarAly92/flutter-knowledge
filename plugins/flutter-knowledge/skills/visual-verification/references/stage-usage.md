# Stage measurement

Record source inspection, calibration, implementation, verification, baseline handoff and final review separately. This is internal evidence bookkeeping; the user still asks for the screen or update in ordinary language. Reuse the task's source facts, selected conventions and harness. Read concise failures and artifact paths rather than complete passing logs or embedded resource payloads.

The verification runner records actual local elapsed time, capture/comparison command attempts and row counts in `results.json.metrics`. These additions do not change comparison settings, statuses or the existing manifest. Local execution does not expose agent tokens: `provider_tokens` remains null. Use available provider counters instead of estimating tokens from elapsed time, characters, files or tool calls.

Use `scripts/stage_usage.py` for immutable stage records and comparisons:

```sh
python3 "<skill-directory>/scripts/stage_usage.py" record --input <measurement.json> --out <events-directory>
python3 "<skill-directory>/scripts/stage_usage.py" summary --events <events-directory>
python3 "<skill-directory>/scripts/stage_usage.py" compare --before <before-events> --after <after-events>
```

A measurement is schema v1 with a stable lowercase `event_id`, `stage`, `workload`, `agent`, `measurements` and `usage`. Stages are `source`, `calibration`, `implementation`, `verification`, `baseline`, `review` and `task_total`. Workload fields are `task`, `fixture_sha256`, `source_sha256`, `coverage_sha256` and `renderer`; use actual task-input and coverage-plan digests, not guessed identities. Agent fields are `provider`, `model` and `plugin`. The plugin identity can differ between before/after measurements; task, fixture, source, coverage, renderer and provider/model must match. Record unsupported or missing measurement capabilities in the task report; they do not weaken visual or behavior gates.

Measurements contain `elapsed_seconds`, `tool_calls`, `captures` and `correction_rounds`. Use measured values or null. Durations/counts cover disjoint events; aggregate event durations are not a wall-clock estimate for overlapping parallel work. For provider-reported usage set `availability: "reported"`, `origin` and a stable `counter_id` identifying the provider request/task report, plus available `input_tokens`, `output_tokens`, `cached_input_tokens` and `total_tokens`. Counters are nonnegative integers or null. Total includes input plus output, and cached input is a subset of input, never an additional total. Do not assign whole-task usage to an invented stage breakdown: record it under `task_total`.

When stage counters are unavailable, record `usage: {"availability": "unavailable", "reason": "<actual missing capability>"}` without numeric token fields. A partial stage cannot receive a fabricated total or savings percentage; a reported total must respect the lower bound of its known components. Reusing one provider counter across multiple stage events is rejected. A workload ledger permits one whole-task total, even when snapshots have different counter IDs; retain other snapshots as raw evidence rather than summing them. Task totals and stage counters remain separate rather than being added together.

`record` binds the measurement file's digest and refuses changing an existing event. The same unchanged event can be resumed without another record. Keep measurement files and their dedicated event directory: summary refuses stale inputs or edited records. Numbers and workload identities are recorded attestations, not independently proven provider billing or runtime fidelity. Retain the original provider/runner evidence alongside them and inspect its origin.

Compare identical recorded stages on the same workload/model/renderer. Report unavailable metrics as unavailable and measured deltas as descriptive, not statistical proof from one run. A smaller capture matrix or missing state cannot count as a usage improvement. During fixes capture affected rows; retain one complete final gate for required affected coverage. Shared-token changes still include their consumers, and inspection/state/behavior checks remain required. Measure actual reductions after those constraints are satisfied rather than promising a percentage in advance.
