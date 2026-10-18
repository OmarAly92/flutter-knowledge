import 'dart:typed_data';

import 'package:core_reference_check/core/data/api/app_interceptor_logger.dart';
import 'package:dio/dio.dart';
import 'package:talker/talker.dart';
import 'package:talker_dio_logger/talker_dio_logger.dart';

Future<void> main() async {
  if (!const bool.fromEnvironment('dart.vm.product')) {
    throw StateError('Compile this smoke probe in product mode');
  }
  var filterCalls = 0;
  final talker = Talker(settings: TalkerSettings(useConsoleLogs: false));
  final dio = Dio()..httpClientAdapter = _Transport();
  dio.interceptors.add(
    AppInterceptorLogger(
      talker: talker,
      settings: TalkerDioLoggerSettings(
        requestFilter: (_) {
          filterCalls++;
          return true;
        },
        responseFilter: (_) {
          filterCalls++;
          return true;
        },
        errorFilter: (_) {
          filterCalls++;
          return true;
        },
      ),
    ),
  );
  final response = await dio
      .get<String>('https://example.test/private-path')
      .timeout(const Duration(seconds: 3));
  if (response.data != 'private-response') throw StateError('Response changed');
  try {
    await dio
        .get<String>('https://example.test/fail')
        .timeout(const Duration(seconds: 3));
    throw StateError('Transport failure was lost');
  } on DioException catch (error) {
    if (error.message != 'private-error') throw StateError('Error changed');
  }
  dio.close(force: true);
  if (filterCalls != 0 || talker.history.isNotEmpty)
    throw StateError('Release logging ran');
  print(
    'Product-mode request, response and error forwarding passed; no logging or filter callbacks.',
  );
}

class _Transport implements HttpClientAdapter {
  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    if (options.path.endsWith('/fail'))
      throw DioException(requestOptions: options, message: 'private-error');
    return ResponseBody.fromString('private-response', 200);
  }

  @override
  void close({bool force = false}) {}
}
