import 'dart:async';

import 'package:core_reference_check/core/data/cache/secure_cache_helper.dart';
import 'package:flutter/foundation.dart';
import 'package:flutter/services.dart';
import 'package:flutter_test/flutter_test.dart';

const _channel = MethodChannel('plugins.it_nomads.com/flutter_secure_storage');

void main() {
  TestWidgetsFlutterBinding.ensureInitialized();

  test(
    'uninitialized secure reads and mutations report readiness errors',
    () async {
      expect(
        () => SecureCacheHelper.get(SecureCacheKeys.credential),
        throwsStateError,
      );
      await expectLater(
        SecureCacheHelper.save('key', 'text'),
        throwsStateError,
      );
      await expectLater(SecureCacheHelper.remove('key'), throwsStateError);
      await expectLater(SecureCacheHelper.clear(), throwsStateError);
    },
  );

  group('secure platform channel', () {
    late _SecureStore store;

    setUp(() async {
      store = _SecureStore();
      debugDefaultTargetPlatformOverride = TargetPlatform.android;
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(_channel, store.respond);
      await SecureCacheHelper.init();
    });

    tearDown(() {
      debugDefaultTargetPlatformOverride = null;
      TestDefaultBinaryMessengerBinding.instance.defaultBinaryMessenger
          .setMockMethodCallHandler(_channel, null);
    });

    test(
      'awaited hydration restores persisted credentials and unknown keys stay null',
      () async {
        store.persisted['key'] = 'persisted';
        final entered = Completer<void>();
        final release = Completer<void>();
        store.beforeCall = (method) async {
          entered.complete();
          await release.future;
        };
        final opening = SecureCacheHelper.init();
        await entered.future;
        try {
          expect(() => SecureCacheHelper.get('key'), throwsStateError);
        } finally {
          release.complete();
          await opening;
        }
        expect(SecureCacheHelper.get('key'), 'persisted');
        expect(SecureCacheHelper.get('unknown'), isNull);
      },
    );

    test(
      'failed hydration preserves storage, blocks stale reads and permits retry',
      () async {
        await SecureCacheHelper.save('key', 'confirmed');
        store.calls.clear();
        store.beforeCall = (method) async =>
            throw PlatformException(code: 'locked');
        await expectLater(
          SecureCacheHelper.init(),
          throwsA(
            isA<PlatformException>().having((e) => e.code, 'code', 'locked'),
          ),
        );
        expect(() => SecureCacheHelper.get('key'), throwsStateError);
        await expectLater(
          SecureCacheHelper.save('other', 'text'),
          throwsStateError,
        );
        expect(store.persisted, {'key': 'confirmed'});
        expect(store.calls, ['readAll']);
        store.beforeCall = null;
        await SecureCacheHelper.init();
        expect(SecureCacheHelper.get('key'), 'confirmed');
      },
    );

    for (final operation in ['save', 'remove', 'clear']) {
      test(
        'failed $operation preserves confirmed mirror and reports platform error',
        () async {
          await SecureCacheHelper.save('key', 'confirmed');
          store.beforeCall = (method) async =>
              throw PlatformException(code: 'denied');
          final changing = switch (operation) {
            'save' => SecureCacheHelper.save('key', 'unconfirmed'),
            'remove' => SecureCacheHelper.remove('key'),
            _ => SecureCacheHelper.clear(),
          };
          await expectLater(
            changing,
            throwsA(
              isA<PlatformException>().having((e) => e.code, 'code', 'denied'),
            ),
          );
          expect(SecureCacheHelper.get('key'), 'confirmed');
          expect(store.persisted, {'key': 'confirmed'});
          store.beforeCall = null;
          await SecureCacheHelper.init();
          expect(SecureCacheHelper.get('key'), 'confirmed');
          await SecureCacheHelper.remove('key');
          expect(SecureCacheHelper.get('key'), isNull);
        },
      );
    }

    test(
      'writes complete before mirror changes and queued hydrate cannot resurrect deletion',
      () async {
        await SecureCacheHelper.save('key', 'confirmed');
        final entered = Completer<void>();
        final release = Completer<void>();
        store.beforeCall = (method) async {
          if (method == 'write') {
            entered.complete();
            await release.future;
          }
        };
        store.calls.clear();
        final saving = SecureCacheHelper.save('key', 'replacement');
        await entered.future;
        final reopening = SecureCacheHelper.init();
        final deleting = SecureCacheHelper.remove('key');
        try {
          expect(SecureCacheHelper.get('key'), 'confirmed');
          expect(store.calls, ['write']);
        } finally {
          release.complete();
          await saving;
          await reopening;
          await deleting;
        }
        expect(store.calls, ['write', 'readAll', 'delete']);
        expect(SecureCacheHelper.get('key'), isNull);
        await SecureCacheHelper.init();
        expect(SecureCacheHelper.get('key'), isNull);
      },
    );

    for (final operation in ['remove', 'clear']) {
      test(
        '$operation changes mirror only after confirmed deletion and survives reopening',
        () async {
          await SecureCacheHelper.save('key', 'confirmed');
          final entered = Completer<void>();
          final release = Completer<void>();
          store.beforeCall = (method) async {
            entered.complete();
            await release.future;
          };
          final deleting = operation == 'remove'
              ? SecureCacheHelper.remove('key')
              : SecureCacheHelper.clear();
          await entered.future;
          try {
            expect(SecureCacheHelper.get('key'), 'confirmed');
          } finally {
            release.complete();
            await deleting;
          }
          expect(SecureCacheHelper.get('key'), isNull);
          store.beforeCall = null;
          await SecureCacheHelper.init();
          expect(SecureCacheHelper.get('key'), isNull);
        },
      );
    }

    test(
      'configured platform options reach the installed storage channel',
      () async {
        for (final platform in [TargetPlatform.android, TargetPlatform.iOS]) {
          debugDefaultTargetPlatformOverride = platform;
          await SecureCacheHelper.init();
          if (platform == TargetPlatform.android) {
            expect(store.options['resetOnError'], 'false');
            expect(store.options['enforceBiometrics'], 'false');
          } else {
            expect(store.options['accessibility'], 'first_unlock_this_device');
          }
        }
      },
    );
  });
}

class _SecureStore {
  final persisted = <String, String>{};
  final calls = <String>[];
  Map<Object?, Object?> options = {};
  Future<void> Function(String method)? beforeCall;

  Future<Object?> respond(MethodCall call) async {
    calls.add(call.method);
    final arguments = call.arguments as Map<Object?, Object?>;
    options = arguments['options'] as Map<Object?, Object?>;
    await beforeCall?.call(call.method);
    switch (call.method) {
      case 'readAll':
        return Map<String, String>.of(persisted);
      case 'write':
        persisted[arguments['key'] as String] = arguments['value'] as String;
      case 'delete':
        persisted.remove(arguments['key'] as String);
      case 'deleteAll':
        persisted.clear();
      default:
        throw MissingPluginException(call.method);
    }
    return null;
  }
}
