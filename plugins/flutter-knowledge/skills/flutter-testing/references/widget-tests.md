# Widget tests

Only when the user asks for them. One file per screen or shared widget, mirroring `lib/`: `test/feature/<feature>/presentation/<screen>_screen/ui/<screen>_screen_test.dart`.

- Mount through the project's widget-test wrapper: `test/helpers/golden_harness.dart` when it exists, otherwise the themed wrapper from `flutter-app-theme` (`ScreenUtilInit` + `MaterialApp(theme: AppTheme.of(skin))` + the configured localization). A bare `MaterialApp` makes `context.tokens` throw.
- Provide the real cubit fed by a mocked repository, the way the route provides it (`BlocProvider(create: (_) => XCubit(repository), child: const XScreen())`); stub the repository before pumping, since the constructor fetch runs on creation.
- Find by what the user sees: the localized text (`find.text(LocaleKeys.trips_title.tr())`), the project wrapper type (`find.byType(PrimaryButton)`) or semantics. Add a `Key` to production code only when text and type are ambiguous, as a `const ValueKey('<screen>_<element>')`.
- `pump()` after a tap; `pump(duration)` with `tokens.motion`-length steps for animations. Avoid `pumpAndSettle` on screens with `AppLoader` or another endless animation: it never settles.
- Assert states and effects the screen owns: the success content, the `AppErrorWidget` on failure, a navigation or snackbar from the Screen listener.
