# Package mechanics under fixed conventions

Use the selected package and the real project APIs. Inspect installed versions and an equivalent implementation before writing code. The guidance below defines the integration contract; it does not supply unverified replacement API calls.

## State management

`flutter-state-management` owns naming, owner-held data, operation states, initial fetch and disposal. Keep those contracts for every backend. For `flutter_bloc` / `bloc`, use its Cubit reference. For Riverpod and Provider, read the concrete references linked by `flutter-state-management`. For GetX, MobX or another configured backend, choose the package mechanism that can expose that same owner and state contract. Keep the project's `XCubit`, `XState`, `...LoadingState` / `...SuccessState` / `...FailureState` names and file conventions; renaming the skill did not authorize renaming Dart types.

An initial fetch belongs to owner creation (the Cubit constructor on the default stack). A backend's own creation/disposal hooks may implement that lifecycle; never move the fetch into the screen. Keep response data on the owner and success states payload-free. Do not substitute an async data container carrying the model as the public state. Controllers remain owned, prefilled and disposed by that owner. If a backend cannot satisfy this contract, identify the incompatibility before implementation.

## UI, routing and DI

Keep the thin Screen and content-only Body. Express the Screen's effects and the Body's selective rebuilding using the selected state API; `BlocListener`, `BlocBuilder` and `buildWhen` are the default mechanisms. Select the exact operation states that require updates.

Routes/composition roots provide state owners; screen widgets do not create them. Preserve per-feature registration ownership, explicit dependencies, per-route state lifetimes and shared service lifetimes. With another router or DI package, adapt route declarations, scoped providers and constructor-argument passing without introducing a second owner. Keep navigation behind the project's extension. Named Navigator routes and get_it factories are the default examples, not permission to replace an already selected router.

## Data, equality and serialization

HTTP packages sit behind the existing `ApiConsumer` contract. Adapt request/response transport there; preserve `GlobalResponse`, the repository's `FutureResult`/`Failure` semantics, connectivity policy and centralized `EndPoints`. Never leak the transport client's response or exception types into presentation.

Equatable is the default comparison mechanism. A selected alternative must preserve field-based equality and the public model/state shape. Keep nullable model fields, fields→constructor→conversion→equality member order where source is authored, and one `XParams` per method. For generated serialization, preserve names, nullability and boundary methods; regenerate through the project's generator, never hand-edit its outputs. Keep existing generator restrictions.

## Localization

`add-translation` owns locale completeness, key naming, collisions and generation. JSON plus `LocaleKeys.xxx.tr()` is the default easy_localization mechanism. For SDK-generated localization or another configured library, use its actual resource format, generated accessor and generator while preserving the English/Arabic meaning and key coverage. No raw user-facing literals or hand-written generated output. Locale changes require an explicit user/project choice.

## Persistence

Keep `drift-local-database` and `hive-local-database` as separate skills. Select only the matching engine skill from config. They own their storage-specific rules; both retain the local data boundary, storage→model mapping, shared resource lifecycle and repository/failure contract.

For another engine, verify its storage semantics and keep those shared boundaries. Do not call Hive instructions applicable to a SQL engine, invent Companion types outside Drift, or migrate existing storage based on a recommendation. Several declared databases need an explicit project/feature choice before writing storage code.

## Theme and supporting packages

`flutter-app-theme` owns tokens, skins and design-value policy. Config does not replace `context.tokens` with a third-party theme API or change the older-project exception. Scaling stays inside typography, motion values inside motion tokens, and shapes inside the shape layer. Adapt selected scaling/motion/shape implementations behind these contracts. Do not add optional animation or shape packages merely because defaults were recorded.

Keep logging behind the logger and preferences behind `CacheHelper`. Adapt a configured network-status implementation inside `NetworkStatus`; its package choice does not change offline repository policy. A missing helper is an implementation task with the existing layer ownership, not a reason to import infrastructure into feature UI.

`packages.secure_storage` is independent of `packages.preferences` and the local database. Follow the [cache storage contract](../../flutter-core/references/core-contracts.md#cache-storage) for `SecureCacheHelper` and native setup. An explicit alternative keeps its verified secure semantics; `none` blocks sensitive persistence rather than redirecting it to preferences or a database.

## Tests and design workflows

Keep the test scenarios and naming/layout conventions. Use the selected mocking API and a state test harness compatible with the selected lifecycle; `mocktail` / `bloc_test` are default mechanisms. Stub collaborators before owner creation. Assert the operation states actually observed, accounting for initial fetch timing without weakening assertions. No mismatched Bloc test helper for a non-Bloc backend.

Golden capture uses the project's configured state, localization, typography, router and cache setup. Preserve real fonts, theme, controlled data, dimensions, insets, and variants. The default example must not introduce an absent package just to render a test. Design readers produce layout/values; screen writing applies the configured mechanics and the same conventions. Reference comparison and baseline approval retain their separate purposes.
