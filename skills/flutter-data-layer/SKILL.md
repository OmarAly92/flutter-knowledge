---
name: flutter-data-layer
description: Flutter data layer conventions — XModel/XParams classes (nullable fields, member order, one params class per method), remote data sources with ApiConsumer and GlobalResponse, repositories returning FutureResult gated on NetworkStatus, EndPoints static methods, and the Failure hierarchy. Use before writing or editing a model, params class, data source, repository, or endpoint in a Flutter project.
---

# Flutter data layer

Invoked by the `flutter-knowledge` skill (or directly via `/flutter-data-layer`) before writing or editing any model, params class, remote data source, repository, or `EndPoints` entry. Related skills: `flutter-feature-structure` for where these files live, `flutter-routing-di` for registering the data source and repository, and `drift-local-database` / `hive-local-database` for any local persistence (do not build that from these rules).

**These conventions are the source of truth.** Existing codebases may be old and inconsistent — where legacy code contradicts this skill, follow the skill and do NOT copy the legacy pattern.

## Data layer

- **Naming suffixes**: models → `XModel` in `data/model/` (extend `Equatable`, `fromJson`/`toJson` as needed); params → `XParams` in `data/model/params/` (extend `Equatable`, implement `toJson()`). **Model fields are always nullable** (`String? name`, `int? total`, ...) — API responses can omit or null out any field, so never declare a model field as required/non-null.
- **One params class per method**: every data source / repository method that takes parameters gets its own dedicated `XParams` class — never share one params class across two methods, even if their fields happen to overlap. If two methods need overlapping fields, that's two separate params classes with duplicated fields, not one shared class.
- **Model member order**: fields first, then the constructor, then `fromJson`, then `toJson` (`props` last, for the `Equatable` override). Keep this order in every model file so they all read the same way.
- **Data source**: abstract class + `*Imp` implementation using `ApiConsumer`. Pass `params.toJson()` as `body`/`queryParameters`. Parse with `GlobalResponse.fromJson(response.data, fromJsonT: XModel.fromJson)` and return `Future<GlobalResponse<XModel>>`. For untyped responses call `GlobalResponse.fromJson(response.data)` without `fromJsonT`; for payloads not wrapped under a `data` key pass `withDataKey: false`. Do NOT catch — let `Failure` bubble to the repository.
- **Repository**: abstract class + `*Imp` implementation returning `FutureResult<GlobalResponse<T>>`, gated on `NetworkStatus`. Check connectivity first; offline → `Result.failure(ServerFailure.noNetwork())`. Wrap the data-source call in `try`/`on Failure catch (error)` → `Result.failure(error)`; success → `Result.success(result)`. Don't unwrap models here.

```dart
@override
FutureResult<GlobalResponse<XModel>> getX(XParams params) async {
  if (await _network.isConnected) {
    try {
      final result = await _remoteDataSource.getX(params);
      return Result.success(result);
    } on Failure catch (error) {
      return Result.failure(error);
    }
  }
  return Result.failure(ServerFailure.noNetwork());
}
```

- **Failure type**: the `Failure` hierarchy and `Result`/`FutureResult` from `lib/core/data/error_handling/`.
- **Endpoints**: for any URL that takes a runtime parameter, add a static method on `EndPoints` (in `lib/core/data/api/end_points.dart`) returning the formatted path — `static String getTripById(String tripId) => '$passengers/trips/$tripId';` — and call it as `_apiConsumer.get(EndPoints.getTripById(tripId))`. NEVER interpolate at the call site: `'${EndPoints.trip}/$tripId'` is forbidden. For URLs with no params, keep using `static const String x = '...';`. `EndPoints` is a `sealed class` holding only static members — do NOT add a private constructor (`EndPoints._()`) to block instantiation; `sealed` already does that. The base URL is a constant on it too (`static const String baseUrl`), and any URL derived from it is a getter built on it — no env file, no `--dart-define`.

## Local database

When a feature needs local persistence — offline storage, caching a remote response locally, or a local-only (no API) feature — invoke the local-database skill that matches the project's storage engine before writing any local data source or storage code. Check `pubspec.yaml`:

- **drift** in the project → invoke `drift-local-database` (via the Skill tool, or `/drift-local-database`). It holds the DAO → LocalDataSource → Repository layering, `Entity`/`Companion` naming, migrations, and the local-only/hybrid repository patterns.
- **hive / hive_ce** in the project → invoke `hive-local-database` (via the Skill tool, or `/hive-local-database`). It holds the Box → LocalDataSource → Repository layering, storage↔model mapping, and the local-only/hybrid repository patterns.

If neither is present yet, pick the one the feature calls for (or ask the user) and follow that skill. Either way, do not invent the persistence layer from memory — each is a distinct, validated set of conventions, not something to reconstruct from the general Data layer rules above.

## What NOT to do

- Do not add `freezed`, `json_serializable`, or `build_runner` unless they are already in `pubspec.yaml`.
- Do not implement local persistence (drift/SQLite tables + DAOs, or Hive boxes, offline caching, local-only or hybrid repositories) without invoking the matching local-database skill first — `drift-local-database` for drift, `hive-local-database` for Hive. Do not invent that layer from memory.
- Do not create model classes the user did not ask for.
- Do not reuse one params class across two data source/repository methods, and do not have a parameterized method share another method's params class. Every method gets its own `XParams`, even when the fields would overlap.
- Do not declare model fields as non-nullable. Assume any API field can be missing or null.
- Do not mix up model member order. Fields, then constructor, then `fromJson`, then `toJson` — every model file in the same order.
- Do not interpolate `EndPoints` constants with runtime params at the call site (no `'${EndPoints.trip}/$tripId'`). Use a static method on `EndPoints`.
- Do not add a private constructor (`X._()`) to a static-only constants class (`EndPoints`, `RoutesStrings`, `AppFonts`, ...) to block instantiation — declare it `sealed class X` instead.
