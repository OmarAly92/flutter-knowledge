import 'dart:async';

import 'package:core_reference_check/core/data/cache/cache_helper.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:shared_preferences/shared_preferences.dart';
import 'package:shared_preferences_platform_interface/shared_preferences_platform_interface.dart';

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test('uninitialized reads and mutations report readiness errors', () async {
    expect(() => CacheHelper.get(CacheKeys.preference), throwsStateError);
    await expectLater(CacheHelper.save('key', 'text'), throwsStateError);
    await expectLater(CacheHelper.remove('key'), throwsStateError);
    await expectLater(Future.sync(CacheHelper.clear), throwsStateError);
  });

  group('preferences boundary', () {
    late _PreferenceStore store;

    setUp(() async {
      SharedPreferences.resetStatic();
      store = _PreferenceStore();
      SharedPreferencesStorePlatform.instance = store;
      await CacheHelper.init();
    });

    test('all supported types survive reopening and deletion', () async {
      final examples = <String, Object>{
        'text': 'العربية',
        'integer': 42,
        'boolean': true,
        'decimal': 2.5,
        'strings': <String>['one', 'two'],
      };
      for (final entry in examples.entries) {
        expect(await CacheHelper.save(entry.key, entry.value), isTrue);
      }
      SharedPreferences.resetStatic();
      await CacheHelper.init();
      for (final entry in examples.entries) {
        expect(CacheHelper.get(entry.key), entry.value);
        expect(CacheHelper.get(entry.key).runtimeType, entry.value.runtimeType);
      }
      expect(await CacheHelper.remove('integer'), isTrue);
      expect(CacheHelper.get('integer'), isNull);
      expect(await CacheHelper.clear(), isTrue);
      await CacheHelper.init();
      for (final key in examples.keys) {
        expect(CacheHelper.get(key), isNull);
      }
    });

    test(
      'list callers cannot mutate saved or retrieved cache contents',
      () async {
        final input = <String>['confirmed'];
        final saving = CacheHelper.save('strings', input);
        input.add('changed while queued');
        expect(await saving, isTrue);
        expect(CacheHelper.get('strings'), ['confirmed']);
        (CacheHelper.get('strings') as List<String>).add('changed after read');
        expect(CacheHelper.get('strings'), ['confirmed']);
        await CacheHelper.init();
        expect(CacheHelper.get('strings'), ['confirmed']);
      },
    );

    test(
      'null and unsupported values leave confirmed preferences intact',
      () async {
        await CacheHelper.save('key', 'confirmed');
        expect(await CacheHelper.save('key', null), isFalse);
        for (final unsupported in <Object>[
          <int>[1],
          {'a': 'b'},
          Object(),
        ]) {
          await expectLater(
            Future.sync(() => CacheHelper.save('key', unsupported)),
            throwsUnsupportedError,
          );
          expect(CacheHelper.get('key'), 'confirmed');
        }
        await CacheHelper.init();
        expect(CacheHelper.get('key'), 'confirmed');
      },
    );

    for (final operation in ['save', 'remove', 'clear']) {
      for (final failure in ['false', 'throw']) {
        test(
          '$operation $failure restores backend view before reopening',
          () async {
            await CacheHelper.save('key', 'confirmed');
            final boundaryError = PlatformException(code: 'write_failed');
            store.beforeMutation = () async {
              if (failure == 'throw') throw boundaryError;
              return false;
            };
            final changing = switch (operation) {
              'save' => CacheHelper.save('key', 'optimistic'),
              'remove' => CacheHelper.remove('key'),
              _ => CacheHelper.clear(),
            };
            if (failure == 'throw') {
              await expectLater(changing, throwsA(same(boundaryError)));
            } else {
              expect(await changing, isFalse);
            }
            expect(CacheHelper.get('key'), 'confirmed');
            store.beforeMutation = null;
            SharedPreferences.resetStatic();
            await CacheHelper.init();
            expect(CacheHelper.get('key'), 'confirmed');
            expect(await CacheHelper.save('key', 'retry'), isTrue);
            expect(CacheHelper.get('key'), 'retry');
          },
        );
      }
    }

    for (final failure in ['false', 'throw']) {
      test(
        'failed recovery after $failure blocks reads until init succeeds',
        () async {
          await CacheHelper.save('key', 'confirmed');
          final boundaryError = PlatformException(code: 'write_failed');
          store.beforeMutation = () async {
            if (failure == 'throw') throw boundaryError;
            return false;
          };
          store.beforeRead = () async =>
              throw PlatformException(code: 'read_failed');
          final changing = CacheHelper.save('key', 'optimistic');
          if (failure == 'throw') {
            await expectLater(
              changing,
              throwsA(
                isA<PlatformException>().having(
                  (error) => error.code,
                  'explicit mutation or recovery failure',
                  isIn(['write_failed', 'read_failed']),
                ),
              ),
            );
          } else {
            try {
              expect(await changing, isFalse);
            } on PlatformException catch (error) {
              expect(error.code, 'read_failed');
            }
          }
          expect(() => CacheHelper.get('key'), throwsStateError);
          await expectLater(CacheHelper.remove('key'), throwsStateError);
          store.beforeRead = null;
          store.beforeMutation = null;
          await CacheHelper.init();
          expect(CacheHelper.get('key'), 'confirmed');
          expect(await CacheHelper.save('key', 'retried'), isTrue);
        },
      );
    }

    for (final stage in ['cached reload', 'initial load']) {
      test('failed $stage invalidates reads and can be retried', () async {
        await CacheHelper.save('key', 'confirmed');
        if (stage == 'initial load') SharedPreferences.resetStatic();
        final boundaryError = PlatformException(code: 'read_failed');
        store.beforeRead = () async => throw boundaryError;
        await expectLater(CacheHelper.init(), throwsA(same(boundaryError)));
        expect(() => CacheHelper.get('key'), throwsStateError);
        store.beforeRead = null;
        await CacheHelper.init();
        expect(CacheHelper.get('key'), 'confirmed');
      });
    }

    test(
      'pending mutation and recovery serialize later init and deletion',
      () async {
        await CacheHelper.save('key', 'confirmed');
        final mutationEntered = Completer<void>();
        final releaseMutation = Completer<void>();
        final recoveryEntered = Completer<void>();
        final releaseRecovery = Completer<void>();
        store.beforeMutation = () async {
          mutationEntered.complete();
          await releaseMutation.future;
          store.beforeMutation = null;
          return false;
        };
        store.beforeRead = () async {
          recoveryEntered.complete();
          await releaseRecovery.future;
          store.beforeRead = null;
        };
        final saving = CacheHelper.save('key', 'optimistic');
        await mutationEntered.future;
        final reopening = CacheHelper.init();
        final deleting = CacheHelper.remove('key');
        try {
          _expectConfirmedOrUnavailable('key', 'confirmed');
          releaseMutation.complete();
          await recoveryEntered.future;
          expect(store.persisted['flutter.key'], 'confirmed');
          _expectConfirmedOrUnavailable('key', 'confirmed');
        } finally {
          if (!releaseMutation.isCompleted) releaseMutation.complete();
          releaseRecovery.complete();
          expect(await saving, isFalse);
          await reopening;
          expect(await deleting, isTrue);
        }
        expect(CacheHelper.get('key'), isNull);
        await CacheHelper.init();
        expect(CacheHelper.get('key'), isNull);
      },
    );
  });
}

void _expectConfirmedOrUnavailable(String key, Object confirmed) {
  try {
    expect(CacheHelper.get(key), confirmed);
  } on StateError {
    return;
  }
}

class _PreferenceStore extends SharedPreferencesStorePlatform {
  final persisted = <String, Object>{};
  Future<bool> Function()? beforeMutation;
  Future<void> Function()? beforeRead;

  @override
  Future<Map<String, Object>> getAll() async {
    await beforeRead?.call();
    return {
      for (final entry in persisted.entries)
        entry.key: entry.value is List<String>
            ? List<String>.of(entry.value as List<String>)
            : entry.value,
    };
  }

  @override
  Future<bool> setValue(String valueType, String key, Object value) async {
    if (!(await beforeMutation?.call() ?? true)) return false;
    persisted[key] = value is List<String> ? List<String>.of(value) : value;
    return true;
  }

  @override
  Future<bool> remove(String key) async {
    if (!(await beforeMutation?.call() ?? true)) return false;
    persisted.remove(key);
    return true;
  }

  @override
  Future<bool> clear() async {
    if (!(await beforeMutation?.call() ?? true)) return false;
    persisted.clear();
    return true;
  }
}
