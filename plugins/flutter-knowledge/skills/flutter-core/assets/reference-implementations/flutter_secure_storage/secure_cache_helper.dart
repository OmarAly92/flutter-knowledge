import 'package:flutter_secure_storage/flutter_secure_storage.dart';

part 'secure_cache_keys.dart';

sealed class SecureCacheHelper {
  static const _storage = FlutterSecureStorage(
    aOptions: AndroidOptions(resetOnError: false, migrateWithBackup: true),
    iOptions: IOSOptions(
      accessibility: KeychainAccessibility.first_unlock_this_device,
    ),
  );
  static final Map<String, String> _values = {};
  static Future<void> _tail = Future<void>.value();
  static bool _ready = false;

  static Future<void> _serialized(Future<void> Function() operation) {
    final next = _tail.then((_) => operation());
    _tail = next.then<void>(
      (_) {},
      onError: (Object error, StackTrace trace) {},
    );
    return next;
  }

  static Future<void> init() => _serialized(() async {
    _ready = false;
    final storedValues = await _storage.readAll();
    _values
      ..clear()
      ..addAll(storedValues);
    _ready = true;
  });

  static void _checkReady() {
    if (!_ready) throw StateError('Secure storage is not initialized');
  }

  static String? get(String key) {
    _checkReady();
    return _values[key];
  }

  static Future<void> save(String key, String value) => _serialized(() async {
    _checkReady();
    await _storage.write(key: key, value: value);
    _values[key] = value;
  });

  static Future<void> remove(String key) => _serialized(() async {
    _checkReady();
    await _storage.delete(key: key);
    _values.remove(key);
  });

  static Future<void> clear() => _serialized(() async {
    _checkReady();
    await _storage.deleteAll();
    _values.clear();
  });
}
