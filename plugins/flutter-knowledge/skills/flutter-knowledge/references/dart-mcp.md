# Dart and Flutter MCP server

The Dart SDK ships an MCP server (`dart mcp-server`, Dart 3.9+). When it is connected to the agent, its tools replace guesswork about the running app and the installed packages. They are optional: every convention and check in these skills still works without them, and the tools never change the architecture, naming, package choices or authorization rules.

## Connecting to a running app

App tools (`hot_reload`, `hot_restart`, `get_runtime_errors`, `widget_inspector`, `flutter_driver_command`) need a Dart Tooling Daemon connection first: `dtd` with `listDtdUris`, then `connect` with the chosen URI. An instance whose working directory is the user's home is usually the IDE's. Connect to an app the user already runs; launching one (`launch_app`, disabled by default) follows the same run/build authorization as any other run in these skills.

## Use per task

| Task | Tool | Rule |
| --- | --- | --- |
| After editing `lib/` with the user's app running | `hot_reload`; `hot_restart` when `main()`, `initState`, static/global state or DI registrations changed | Then `get_runtime_errors`. Skip for comment-only edits and for files outside `lib/`. A reload is not a test or a review. |
| Runtime exception, red screen, layout error | `get_runtime_errors`, then `widget_inspector` `get_widget_tree` | Fix the first real error in the stack, reload, and read the errors again. See `flutter-responsive-layout` → Fix a layout error. |
| Checking an installed package API before using it | `read_package_uris` (`package:dio/dio.dart`), `rip_grep_packages` | Preferred over memory whenever a skill says to verify the installed API. |
| Finding an existing widget, helper or class before writing one | `lsp` `resolveWorkspaceSymbol` | Same reuse rule as `flutter-feature-structure`: read the match and its API, then reuse or extend it. |
| Analysis and tests during implementation | `analyze_files`; `run_tests` (disabled by default) | Same scope rules as the CLI. `flutter-review` remains the final gate and runs its own commands. |
| Searching pub.dev | `pub_dev_search` | Finding a package never authorizes adding it; dependencies follow `flutter-init` and the task scope. |
| Exploring a user flow in the running app | `flutter_driver_command` (tap, enter text, scroll, wait, read text, screenshot) | Needs the driver entry point from `flutter-testing` → Integration tests. A driver screenshot is not design evidence; design comparison uses `visual-verification` and goldens. |

`run_tests`, `dart_format`, `dart_fix` and `create_project` need `--enable cli`; `launch_app`, `stop_app`, `list_devices`, `get_app_logs` and `list_running_apps` need `--enable flutter_app_lifecycle`. Do not run `dart_fix` across a project as a side effect; it can rewrite unrelated files.

## Other Flutter skill plugins

The official `dart-flutter` plugin and other skill packs can be installed next to this one. Where their guidance differs from these skills (routing package, HTTP client, localization system, architecture layers, JSON approach, error handling, test layout), these skills and the project configuration win. Use their tools and API facts; do not adopt their structure.
