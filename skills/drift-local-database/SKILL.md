---
name: drift-local-database
description: Drift/SQLite local persistence conventions for a Flutter feature — tables, DAOs, entities, migrations, local-only and hybrid (remote+local) repositories. Use when the user asks to add local storage, persist data locally, add offline support, cache API responses locally, or work with drift/SQLite in this Flutter project.
---

# Local database (drift)

Invoked by the `flutter-knowledge` skill (or directly via `/drift-local-database`) whenever a feature needs local persistence — these are the validated conventions; do not invent this layer from memory.

Uses `drift` + `drift_flutter`, with `drift_dev` + `build_runner` in `dev_dependencies` — this pair is the one sanctioned codegen exception to the "no freezed/json_serializable/build_runner" rule, and only when a feature actually needs local storage. The layering is **DAO → LocalDataSource → Repository → Cubit**, one direction only — each layer knows just the one below it, and drift types (`XEntity`, `XsCompanion`, table classes) never cross past the LocalDataSource.

```
lib/
  core/
    database/
      app_database.dart              # the one @DriftDatabase — owns schemaVersion + migration
      tables/
        <tableName>/
          <tableName>_table.dart     # Table + @DataClassName('XEntity')
          <tableName>_dao.dart       # @DriftAccessor, every method chains .handleLocalFailure()
  feature/
    <feature>/
      data/
        data_source/<feature>_local_data_source.dart  # takes the DAO(s); maps Entity <-> Model, params -> Companion
        model/<feature>_model.dart                    # XModel — the domain contract, DB-agnostic shape
        model/params/                                 # AddXParams / UpdateXParams
        repository/<feature>_repository.dart
```

The folder/file name under `tables/` is the **table's** name, not the feature's — they happen to match for a feature with exactly one table (`budget` feature → `tables/budget/`), but a feature backed by more than one table gets one sibling subfolder per table, each named for that table, not all nested under one feature-named folder.

## Database

One `AppDatabase` class in `lib/core/database/app_database.dart`, built with `drift_flutter`'s `driftDatabase(name: ...)`, plus an `AppDatabase.forTesting(super.executor)` constructor used only in tests (with an in-memory executor). Registered once as a lazy singleton in `ServiceLocator._coreSetup()`. Features never open their own database.

```dart
@DriftDatabase(tables: [Budgets], daos: [BudgetDao])
class AppDatabase extends _$AppDatabase {
  AppDatabase() : super(driftDatabase(name: 'app_db_name'));

  AppDatabase.forTesting(super.executor);

  @override
  int get schemaVersion => 1;

  @override
  MigrationStrategy get migration =>
      MigrationStrategy(onCreate: (m) => m.createAll());
}
```

## Tables and DAOs

**Tables and DAOs live in `lib/core/database/tables/<tableName>/`** — `<tableName>_table.dart` + `<tableName>_dao.dart` — NEVER inside `lib/feature/<feature>/data/`. The folder/file name is the **table's** name, not the feature's; a feature with more than one table gets one subfolder per table. Both get listed in `AppDatabase`'s `@DriftDatabase(tables: [...], daos: [...])`, then run `build_runner`. The row class is named `<X>Entity` via `@DataClassName('XEntity')` on the table — `XModel` stays reserved for the feature's own model.

**Why core, not the feature**: `AppDatabase` is one shared drift-generated class — its `@DriftDatabase` annotation must list every table/DAO up front, and its single `schemaVersion`/`MigrationStrategy` reason about all of them together. That means `app_database.dart` has to import each table — if a table lived inside `lib/feature/<feature>/...`, a `core` file would end up depending on a `feature`, which inverts the one dependency direction this codebase never allows (`feature` → `core`, never the reverse). Keeping tables/DAOs in `core/database/tables/<tableName>/` keeps every import core→core or feature→core, and doubles as the one place to read the app's whole SQLite schema when writing a migration.

```dart
@DataClassName('BudgetEntity')
class Budgets extends Table {
  IntColumn get id => integer().autoIncrement()();
  TextColumn get name => text()();
  RealColumn get limitAmount => real()();
  RealColumn get spentAmount => real().withDefault(const Constant(0))();
  DateTimeColumn get startDate => dateTime()();
  DateTimeColumn get endDate => dateTime().nullable()();
  DateTimeColumn get createdAt =>
      dateTime().clientDefault(() => DateTime.now())();
}
```

`@DriftAccessor(tables: [...])` extending `DatabaseAccessor<AppDatabase>` with the generated `_$XDaoMixin`, constructed with `XDao(super.db)`. Every method — `Future` or `Stream`, read or write — chains `.handleLocalFailure()` (the extension in `core/error_handling/drift_error_handler/drift_error_handler.dart` that catches any drift/sqlite exception and rethrows it as `LocalFailure`, a `Failure` subtype). This is why nothing above the DAO needs a try/catch for local errors.

```dart
@DriftAccessor(tables: [Budgets])
class BudgetDao extends DatabaseAccessor<AppDatabase> with _$BudgetDaoMixin {
  BudgetDao(super.db);

  Future<List<BudgetEntity>> getAllBudgets() =>
      select(budgets).get().handleLocalFailure();

  Stream<List<BudgetEntity>> watchAllBudgets() =>
      select(budgets).watch().handleLocalFailure();

  Future<int> insertBudget(BudgetsCompanion budget) =>
      into(budgets).insert(budget).handleLocalFailure();

  Future<bool> updateBudget(BudgetsCompanion budget) =>
      update(budgets).replace(budget).handleLocalFailure();

  Future<int> deleteBudget(int id) =>
      (delete(budgets)..where((t) => t.id.equals(id))).go().handleLocalFailure();
}
```

## Local data source

Same shape as remote — abstract class + `*Imp`, named `XLocalDataSource` / `XLocalDataSourceImp`, in `data/data_source/<feature>_local_data_source.dart` — but constructed with the **DAO**, not `AppDatabase` directly. Its only job is translation: `XEntity` → `XModel` via `factory XModel.fromDB(XEntity e)` on reads, params → `XsCompanion` on writes. Do NOT catch here — `LocalFailure` already comes from the DAO.

```dart
abstract class BudgetLocalDataSource {
  Future<List<BudgetModel>> getBudgets();
  Stream<List<BudgetModel>> watchBudgets();
  Future<int> addBudget(AddBudgetParams params);
  Future<bool> updateBudget(UpdateBudgetParams params);
  Future<int> deleteBudget(int id);
}

class BudgetLocalDataSourceImp implements BudgetLocalDataSource {
  BudgetLocalDataSourceImp(this._dao);

  final BudgetDao _dao;

  @override
  Future<List<BudgetModel>> getBudgets() async {
    final entities = await _dao.getAllBudgets();
    return entities.map(BudgetModel.fromDB).toList();
  }

  @override
  Stream<List<BudgetModel>> watchBudgets() => _dao.watchAllBudgets().map(
    (entities) => entities.map(BudgetModel.fromDB).toList(),
  );

  @override
  Future<int> addBudget(AddBudgetParams params) => _dao.insertBudget(
    BudgetsCompanion.insert(
      name: params.name,
      limitAmount: params.limitAmount,
      startDate: params.startDate,
      spentAmount: params.spentAmount == null
          ? const Value.absent()
          : Value(params.spentAmount!),
      endDate: params.endDate == null
          ? const Value.absent()
          : Value(params.endDate),
    ),
  );

  @override
  Future<bool> updateBudget(UpdateBudgetParams params) => _dao.updateBudget(
    BudgetsCompanion(
      id: Value(params.id),
      name: Value(params.name),
      limitAmount: Value(params.limitAmount),
      startDate: Value(params.startDate),
      spentAmount: params.spentAmount == null
          ? const Value.absent()
          : Value(params.spentAmount!),
      endDate: params.endDate == null
          ? const Value.absent()
          : Value(params.endDate),
    ),
  );

  @override
  Future<int> deleteBudget(int id) => _dao.deleteBudget(id);
}
```

Use `XsCompanion.insert(...)` for adds (required columns are named params, matching the table) and a plain `XsCompanion(...)` for updates (every field wrapped in `Value(...)`, since an omitted field means "don't touch this column"). Either way, a nullable param becomes `param == null ? const Value.absent() : Value(param)` — never pass a raw nullable straight into a field that isn't `Value.absent()`-aware.

## Model and params

- **Model**: same `Equatable`, all-nullable-fields shape as an API model, but member order is fields → constructor → `fromDB` → `props` — a local-only model has no `fromJson`/`toJson`; reads come from `fromDB`, writes go through a Params class instead of `Model.toJson()`.
- **Params**: one class per write method, same as the API convention — `AddXParams` (no `id`; it's autoincrement) and `UpdateXParams` (`id` required). Unlike API params, local params do NOT implement `toJson()` — the local data source reads their fields directly to build the `Companion`. Their fields are properly required/nullable (required for what the write genuinely needs, nullable only for what's optional) rather than blanket-nullable like a model — these are built by trusted in-app callers, not parsed from external JSON.

**Why the model stays in the feature (not next to `Entity` in core)**: `XEntity` is drift's row shape — an implementation detail of the storage engine (SQL column types, drift codegen, `Companion`s). `XModel` is the domain contract the Repository/Cubit/UI actually consume, and it looks the same whether the feature is remote, local, or hybrid. The LocalDataSource is the one seam that converts between them (`fromDB`), so nothing above it — Repository, Cubit, UI — ever needs to know drift exists.

## DI

Three registrations per feature, not two — the DAO is its own injectable, sitting between `AppDatabase` and the local data source:

```dart
sl.registerLazySingleton<BudgetRepository>(
  () => BudgetRepositoryImp(sl<BudgetLocalDataSource>()),
);
sl.registerLazySingleton<BudgetLocalDataSource>(
  () => BudgetLocalDataSourceImp(sl<BudgetDao>()),
);
sl.registerLazySingleton<BudgetDao>(() => BudgetDao(sl<AppDatabase>()));
```

## Pagination and schema changes

- **Pagination**: only add page/limit handling for lists that can grow unbounded (e.g. transactions) — apply the feature's `XParams` page/limit via drift's `limit(params.limit, offset: (params.page - 1) * params.limit)`. A small, naturally bounded list (e.g. budgets, settings) is fine to return whole via `select(db.xTable).get()` — don't reflexively paginate every list read.
- **Schema changes**: bump `schemaVersion` and handle it in `migration`'s `MigrationStrategy` — never edit a released table in place.

## Local-only feature

No API at all: the repository takes just the local data source, skips the `NetworkStatus` gate entirely, must not import `drift` or reference `XCompanion`/`XEntity` (that mapping already happened one layer down), and returns `FutureResult<T>` with the models directly (no `GlobalResponse` — that envelope belongs to the API):

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

- Caching methods are named `cacheX(...)` and upsert (insert-or-replace) so re-fetching a page never duplicates rows.
- Plain remote-only features keep the existing shape: offline → `Result.failure(ServerFailure.noNetwork())`. Only use the hybrid pattern when the feature is actually meant to work offline.

## What NOT to do

- Do not put a drift `Table` or `@DriftAccessor` class inside `lib/feature/...`. Tables and DAOs live in `lib/core/database/tables/<tableName>/`, named for the table, not the feature.
- Do not name a `@DataClassName` row class anything other than `<X>Entity`, and do not reuse `XModel` for it.
- Do not skip `.handleLocalFailure()` on a DAO method (`Future` or `Stream`) — it's how drift/sqlite exceptions become `LocalFailure`.
- Do not let `XCompanion`/`XEntity` leak past the local data source — no `drift` import in a repository or presentation code; map to `XModel`/params one layer down.
- Do not give a local write Params class `toJson()` or blanket-nullable fields like an API model — its fields should be required/nullable based on what the write actually needs.
- Do not reflexively paginate every local list read — only add page/limit handling for lists that can grow unbounded (e.g. transactions); a small bounded list (e.g. budgets) can return whole.
- Do not use the hybrid offline-fallback pattern for ordinary remote features — offline still returns `ServerFailure.noNetwork()` unless the feature is explicitly meant to work offline. And in hybrid repositories, do not skip caching the remote response into local on success.
- Do not open a database inside a feature or data source, and do not add `drift`/`drift_flutter`/`drift_dev`/`build_runner` for a feature that doesn't need local storage. One `AppDatabase` in `lib/core/database/`, injected via the service locator.
