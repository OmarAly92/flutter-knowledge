---
name: hive-local-database
description: Hive (hive_ce) local persistence conventions for a Flutter feature — boxes, local data sources, storage↔model mapping, local-only and hybrid (remote+local) repositories. Use when the user asks to add local storage, persist data locally, add offline support, cache API responses locally, or work with hive/hive_ce in this Flutter project.
---

# Local database (Hive)

Invoked by the `flutter-knowledge` skill (or directly via `/hive-local-database`) whenever a Hive-backed feature needs local persistence — use this skill when the project's local storage is Hive, and the `drift-local-database` skill when it is drift (check `pubspec.yaml`).

**Follow the project first.** If the codebase already uses Hive with its own conventions, read an existing Hive feature and mirror it — names, box setup, mapping. Only depart from it where its shape is genuinely weak (storage types leaking above the data source, boxes opened mid-feature, no failure translation), and improve just that. The conventions below are the greenfield default when there is nothing to follow, and the yardstick for what "weak" means.

Uses `hive_ce` + `hive_ce_flutter` (the maintained community fork — original `hive`/`hive_flutter` is abandoned; if a project already runs original `hive`, follow it rather than migrating it here). The layering is **Box → LocalDataSource → Repository → Cubit**, one direction only — there is no DAO layer (Hive has no generated accessor), so the LocalDataSource holds the box directly.

## The one rule that matters most

**The Hive storage representation never crosses past the LocalDataSource.** Whatever a box stores — a `Map<String, dynamic>` (the default) or a typed `@HiveType XHiveModel` if the project uses adapters — is a storage detail. The LocalDataSource is the *only* seam that knows Hive exists: it maps storage → `XModel` on reads and `params` → storage on writes. Repository, Cubit, and UI import no `hive_ce`, hold no `Box`, and never see a stored `Map` or a `@HiveType` class. If a feature already has a Hive model, **do not depend on it directly above the data source** — map it to the domain `XModel` at the boundary.

```
lib/
  core/
    database/
      hive_boxes.dart                # opens + registers every box; features never open their own
    error_handling/
      hive_error_handler/
        hive_error_handler.dart      # handleLocalFailure() → LocalFailure
  feature/
    <feature>/
      data/
        data_source/<feature>_local_data_source.dart  # holds the Box; maps stored Map <-> Model, params -> Map
        model/<feature>_model.dart                     # XModel — the domain contract, storage-agnostic shape
        model/params/                                  # AddXParams / UpdateXParams
        repository/<feature>_repository.dart
```

## Boxes and initialization

`Hive.initFlutter()` runs once at bootstrap, before `runApp`, and every box a feature needs is opened there and registered in the `ServiceLocator` — features never call `Hive.openBox` themselves, exactly as drift features never open the database. One box per feature (or per stored type); its opened `Box` is what gets injected, mirroring how drift injects the one `AppDatabase`.

```dart
Future<void> initHive() async {
  await Hive.initFlutter();
  final budgetBox = await Hive.openBox<Map>('budgets');
  sl.registerSingleton<Box<Map>>(budgetBox, instanceName: 'budgets');
}
```

Store the JSON map keyed by the model's own `id` (`box.put(model.id, json)`) so update and delete are direct lookups; reads come off `box.values`. Hive has no autoincrement — the domain `id` is the app's to supply (a uuid, or the id the remote returned for a cached row). Use `box.add(json)` (auto int key) only for a feature that genuinely has no stable domain id.

## Error handling

A `handleLocalFailure()` helper — the Hive analogue of drift's — lives in `core/error_handling/hive_error_handler/hive_error_handler.dart`. It catches any `HiveError`/storage exception and rethrows it as `LocalFailure` (a `Failure` subtype). Because there is no DAO, the wrap happens on the **box calls inside the LocalDataSource** — so Repository and Cubit still never `try/catch` a local error, just like the drift layering.

```dart
extension HiveFutureFailure<T> on Future<T> {
  Future<T> handleLocalFailure() async {
    try {
      return await this;
    } on Failure {
      rethrow;
    } catch (error, stackTrace) {
      throw LocalFailure.fromHive(error, stackTrace);
    }
  }
}

T handleLocalFailureSync<T>(T Function() op) {
  try {
    return op();
  } on Failure {
    rethrow;
  } catch (error, stackTrace) {
    throw LocalFailure.fromHive(error, stackTrace);
  }
}
```

Synchronous reads (`box.values`, `box.get`) go through `handleLocalFailureSync(...)`; async writes (`box.put`, `box.delete`) chain `.handleLocalFailure()`.

## Local data source

Same shape as the remote data source — abstract class + `*Imp`, named `XLocalDataSource` / `XLocalDataSourceImp`, in `data/data_source/<feature>_local_data_source.dart` — but constructed with the **`Box`**, not `Hive` directly. Its only job is translation: stored `Map` → `XModel` via `factory XModel.fromDB(Map<String, dynamic> map)` on reads, `params` → `Map` on writes. Every box call goes through the failure guard; do not add a second `try/catch` above it.

```dart
abstract class BudgetLocalDataSource {
  Future<List<BudgetModel>> getBudgets();
  Stream<List<BudgetModel>> watchBudgets();
  Future<void> addBudget(AddBudgetParams params);
  Future<void> updateBudget(UpdateBudgetParams params);
  Future<void> deleteBudget(String id);
}

class BudgetLocalDataSourceImp implements BudgetLocalDataSource {
  BudgetLocalDataSourceImp(this._box);

  final Box<Map> _box;

  @override
  Future<List<BudgetModel>> getBudgets() async => handleLocalFailureSync(
    () => _box.values
        .map((e) => BudgetModel.fromDB(Map<String, dynamic>.from(e)))
        .toList(),
  );

  @override
  Stream<List<BudgetModel>> watchBudgets() =>
      _box.watch().asyncMap((_) => getBudgets());

  @override
  Future<void> addBudget(AddBudgetParams params) =>
      _box.put(params.id, params.toDb()).handleLocalFailure();

  @override
  Future<void> updateBudget(UpdateBudgetParams params) =>
      _box.put(params.id, params.toDb()).handleLocalFailure();

  @override
  Future<void> deleteBudget(String id) =>
      _box.delete(id).handleLocalFailure();
}
```

`box.watch()` emits a `BoxEvent` per change, not the list — so `watchX()` maps each event to a fresh full read (`asyncMap((_) => getX())`), returning `Stream<List<XModel>>` to match drift's `watchX()` contract. Reading a stored value back gives a `Map<dynamic, dynamic>`, so wrap it with `Map<String, dynamic>.from(...)` before handing it to `fromDB`. A write is an upsert on the same key (`box.put(id, ...)`), so re-caching a row never duplicates it.

**If the project stores a typed `@HiveType XHiveModel` instead of a map**: the box is `Box<XHiveModel>`, the LocalDataSource maps `XHiveModel` → `XModel` via `factory XModel.fromDB(XHiveModel e)` and `params` → `XHiveModel` on writes. Everything above is unchanged — the typed class stays behind the data source exactly as the map does.

## Model and params

- **Model**: same `Equatable`, all-nullable-fields shape as an API model, with member order fields → constructor → `fromDB` → `props`. A local-only model has no `fromJson`/`toJson`; reads come from `fromDB` (a stored `Map` or a `@HiveType` object), writes go through a Params class instead of `Model.toJson()`. If the feature is hybrid and the model already has `fromJson`/`toJson` for the API, those may double as the storage codec — but the read seam is still named `fromDB`.
- **Params**: one class per write method — `AddXParams` and `UpdateXParams` (`id` required; unlike drift there is no autoincrement, so an add supplies its `id` too). A local Params class exposes a `toDb()` returning the `Map` (or `XHiveModel`) to store — the storage analogue of a `Companion` — and does **not** implement `toJson()`. Its fields are properly required/nullable by what the write needs, not blanket-nullable like a model, because these are built by trusted in-app callers.

**Why the model stays in the feature (not a storage concern):** the stored `Map`/`XHiveModel` is how Hive keeps the row; `XModel` is the domain contract the Repository/Cubit/UI consume, and it looks the same whether the feature is remote, local, or hybrid. The LocalDataSource is the one place that converts between them, so nothing above it ever needs to know Hive exists.

## DI

Two registrations per feature — no DAO layer, so the LocalDataSource takes the injected `Box` directly:

```dart
sl.registerLazySingleton<BudgetRepository>(
  () => BudgetRepositoryImp(sl<BudgetLocalDataSource>()),
);
sl.registerLazySingleton<BudgetLocalDataSource>(
  () => BudgetLocalDataSourceImp(sl<Box<Map>>(instanceName: 'budgets')),
);
```

## Local-only feature

No API at all: the repository takes just the local data source, skips the `NetworkStatus` gate entirely, must not import `hive_ce` or reference a `Box`/stored `Map`/`XHiveModel` (that mapping already happened one layer down), and returns `FutureResult<T>` with the models directly (no `GlobalResponse` — that envelope belongs to the API):

```dart
@override
FutureResult<List<XModel>> getX(XParams params) async {
  try {
    final result = await _localDataSource.getX(params);
    return Result.success(result);
  } on Failure catch (error) {
    return Result.failure(error);
  }
}
```

## Hybrid feature (remote + local fallback)

Remote when online, local fallback when offline: the repository takes remote + local + `NetworkStatus`. Online → call remote, cache the response into local, return it. Offline → read from local instead of returning `ServerFailure.noNetwork()`. The return type stays `FutureResult<GlobalResponse<T>>` — the offline branch wraps the cached models in a `GlobalResponse` so the cubit never knows which source answered:

```dart
@override
FutureResult<GlobalResponse<List<XModel>>> getX(XParams params) async {
  if (await _network.isConnected) {
    try {
      final result = await _remoteDataSource.getX(params);
      await _localDataSource.cacheX(result.data ?? []);
      return Result.success(result);
    } on Failure catch (error) {
      return Result.failure(error);
    }
  }
  final cached = await _localDataSource.getX(params);
  return Result.success(GlobalResponse(data: cached));
}
```

- Caching methods are named `cacheX(...)` and upsert by key (`box.put(model.id, ...)`) so re-fetching a page never duplicates rows.
- Plain remote-only features keep the existing shape: offline → `Result.failure(ServerFailure.noNetwork())`. Only use the hybrid pattern when the feature is actually meant to work offline.

## What NOT to do

- Do not let a stored `Map` or a `@HiveType XHiveModel` cross past the LocalDataSource — no `hive_ce` import, no `Box`, no stored type in a repository, cubit, or widget. Map to `XModel`/params at the data source.
- Do not open a box inside a feature or data source. Boxes are opened once at bootstrap and registered in the `ServiceLocator`; features receive the injected `Box`.
- Do not skip `handleLocalFailure()` / `handleLocalFailureSync()` on a box call — it is how Hive exceptions become `LocalFailure`, which is why nothing above the data source needs a local `try/catch`.
- Do not give a local write Params class `toJson()` or blanket-nullable fields like an API model — expose `toDb()` and make fields required/nullable by what the write needs.
- Do not have `watchX()` return the raw `Stream<BoxEvent>` — map each event to a full re-read so it yields `Stream<List<XModel>>`, matching the drift contract.
- Do not use the hybrid offline-fallback pattern for ordinary remote features — offline still returns `ServerFailure.noNetwork()` unless the feature is explicitly meant to work offline. And in hybrid repositories, do not skip caching the remote response into local on success.
- Do not add `hive_ce`/`hive_ce_flutter` for a feature that doesn't need local storage, and do not migrate a project that already runs original `hive` to `hive_ce` as part of a feature.
- Do not override a project's existing, working Hive conventions just to match this skill — follow them, and improve only the genuinely weak parts (leaked storage types, boxes opened mid-feature, missing failure translation).
