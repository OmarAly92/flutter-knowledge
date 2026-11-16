# Integration tests

Only when the user asks for them. They run the real app on a device or emulator, so they follow the same run authorization as any app launch.

```
integration_test/<flow>_test.dart     # one user flow per file
test_driver/integration_test.dart     # host script for flutter drive
test_driver/app.dart                  # driver entry for flutter_driver / MCP exploration
```

- Add `integration_test` (and `flutter_driver` for the driver entry) as SDK dev dependencies only when creating these files.
- Each test calls `IntegrationTestWidgetsFlutterBinding.ensureInitialized()`, then starts the real startup with `app.main()` so DI, localization, cache and the router are the production ones. Ask before testing against a real backend; otherwise point the app at the project's existing test environment.
- The driver extension never goes in `lib/main.dart`. `test_driver/app.dart` enables it and calls the real entry point; run it with `flutter run -t test_driver/app.dart` to explore a flow through `flutter_driver_command` in the [Dart MCP server](../../flutter-knowledge/references/dart-mcp.md), then write the steps that worked as an `integration_test/` test:

```dart
import 'package:flutter_driver/driver_extension.dart';
import 'package:<app>/main.dart' as app;

void main() {
  enableFlutterDriverExtension();
  app.main();
}
```

- Finders and pumping follow the widget-test rules above; scroll lazily built lists into view with `scrollUntilVisible` before tapping.
