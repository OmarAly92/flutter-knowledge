# Tested core building blocks

Read only the implementation needed by the selected core responsibility, after
inspecting the target's contracts, callers, package selection and installed APIs.
These references reduce re-derivation of fragile mechanics; the owning skills and
[core contracts](core-contracts.md) remain authoritative.

| Missing or incomplete component | Reference and applicability |
| --- | --- |
| Cached ordinary preferences | [CacheHelper](../assets/reference-implementations/shared_preferences/cache_helper.dart) uses the legacy cached `shared_preferences` API and keeps all supported value types. Retain the target's `cache_keys.dart` part and existing keys. A working async preference API keeps its existing contract; do not replace it with this synchronous getter. |
| Secure string storage | [SecureCacheHelper](../assets/reference-implementations/flutter_secure_storage/secure_cache_helper.dart) uses `flutter_secure_storage`, serialized readiness/mutations and a confirmed-value mirror. Retain `secure_cache_keys.dart`, identifiers and the target's platform/accessibility policy. Native installation and runtime checks still follow the core contract. |
| Debug HTTP diagnostics | [AppInterceptorLogger](../assets/reference-implementations/dio_talker/app_interceptor_logger.dart) uses Dio with Talker. Preserve original transport objects, configured filtering and client wiring. Its redacted cURL is a diagnostic skeleton, not a replayable request. Keep consumer installation debug-gated and verify the target's installed logger API. |
| Material component colors and states | The theme owner supplies [component mapping fragments](../../flutter-app-theme/references/component-mappings.md) for button fill/ink and field borders. Merge only missing/incorrect mappings into the existing builder/wrapper; they do not supply a palette or replacement theme. |

The logger uses generated labels for untrusted payload/query/form/unknown-header
names and redacts scalar values; the configured origin hostname remains
diagnostic metadata. Adapt that policy if the target treats hostnames as private.
Filters run on original objects, while trusted formatters/converters receive safe
copies and must not inject independent secrets from their closures.

Use a reference directly only for a missing component with compatible default
mechanics. For an incomplete component, inspect the defect and adapt the relevant
behavior while preserving its public signatures, imports, keys, registrations,
styling and callers. A working equivalent needs no edit. Alternative configured
packages require their verified mechanisms under the same conventions; do not
install or switch a backend to make an example fit. Test fixture pins are not
application dependency requirements or proof for every version combination.

The reference files contain no application key declarations, endpoints, auth
policy, branding or palette values. Keep project-specific parts and initialization
ownership in the target project; copying a helper does not complete registration,
startup, native setup or the rest of core. These files are not a whole-core
generator or an automatic migration command.

## Maintainer validation

In the flutter-knowledge-skill source checkout,
`tests/fixtures/core-references/manifest.json` records exact tested package
versions and source assembly. It copies the shipped
files and inserts the theme fragments verbatim, then formats only the fixture.
These commands are maintainer checks from that source checkout, not commands
to run in a Flutter app or an installed plugin cache:

```sh
python3 tests/check_core_references.py
python3 tests/check_core_references.py --only cache
python3 tests/check_core_references.py --only logger
python3 tests/check_core_references.py --only theme
```

Resolution is offline by default; `--fetch` permits fixture dependency downloads.
`--out <new-or-empty-directory>` retains a fixture and its full test log. The
runner never writes into an existing nonempty application and never installs a
Flutter SDK. It analyzes the assembled sources and requires a complete successful
machine test report; failed, incomplete or skipped cases cannot count as success.
The logger fixture also compiles and executes a product-mode Dart smoke probe
to check original transport forwarding without logs or filter callbacks.

These are host contract/widget checks. They do not certify a target app, native
storage, a supplied design, or a different package API. After adapting a reference,
verify its actual consumers and the selected core scope normally.
