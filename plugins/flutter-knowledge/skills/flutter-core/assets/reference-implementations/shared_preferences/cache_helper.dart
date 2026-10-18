import 'package:shared_preferences/shared_preferences.dart';

part 'cache_keys.dart';

sealed class CacheHelper {
  static late SharedPreferences _preferences;
  static Future<void> _tail = Future<void>.value();
  static bool _ready = false;

  static Future<T> _serialized<T>(Future<T> Function() operation) {
    final next = _tail.then((_) => operation());
    _tail = next.then<void>(
      (_) {},
      onError: (Object error, StackTrace trace) {},
    );
    return next;
  }

  static Future<void> init() => _serialized(() async {
    _ready = false;
    _preferences = await SharedPreferences.getInstance();
    await _preferences.reload();
    _ready = true;
  });

  static void _checkReady() {
    if (!_ready) throw StateError('Preferences are not initialized');
  }

  static dynamic get(String key) {
    _checkReady();
    final cached = _preferences.get(key);
    return cached is List ? _preferences.getStringList(key) : cached;
  }

  static Future<bool> _mutate(Future<bool> Function() operation) =>
      _serialized(() async {
        _checkReady();
        _ready = false;
        var confirmed = false;
        try {
          confirmed = await operation();
          return confirmed;
        } finally {
          if (confirmed) {
            _ready = true;
          } else {
            await _recover();
          }
        }
      });

  static Future<void> _recover() async {
    try {
      await _preferences.reload();
      _ready = true;
    } catch (_) {
      _ready = false;
    }
  }

  static Future<bool> save(String key, dynamic value) {
    if (value == null) return Future<bool>.value(false);
    final snapshot = value is List<String> ? List<String>.of(value) : value;
    return switch (snapshot) {
      String v => _mutate(() => _preferences.setString(key, v)),
      int v => _mutate(() => _preferences.setInt(key, v)),
      bool v => _mutate(() => _preferences.setBool(key, v)),
      double v => _mutate(() => _preferences.setDouble(key, v)),
      List<String> v => _mutate(() => _preferences.setStringList(key, v)),
      _ => Future<bool>.error(UnsupportedError('Unsupported preference type')),
    };
  }

  static Future<bool> remove(String key) =>
      _mutate(() => _preferences.remove(key));

  static Future<bool> clear() => _mutate(() => _preferences.clear());
}
