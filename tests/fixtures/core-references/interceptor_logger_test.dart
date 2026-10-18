import 'dart:convert';
import 'dart:typed_data';

import 'package:core_reference_check/core/data/api/app_interceptor_logger.dart';
import 'package:dio/dio.dart';
import 'package:flutter_test/flutter_test.dart';
import 'package:talker/talker.dart';
import 'package:talker_dio_logger/talker_dio_logger.dart';
import 'package:talker_dio_logger/dio_logs.dart';

void main() {
  test(
    'JSON logs redact every surface while transport and caller keep originals',
    () async {
      final harness = _Harness(
        settings: const TalkerDioLoggerSettings(
          printRequestHeaders: true,
          printRequestExtra: true,
          printResponseHeaders: true,
          printResponseTime: true,
          printResponseRedirects: true,
        ),
      );
      addTearDown(harness.close);
      final payload = {
        'email': 'body@example.test',
        'profile': [
          {'label': 'private-label', 'phone': 20123456789},
        ],
        'password': 'body-password',
        'identifier': 202400001,
      };
      final response = await harness.dio
          .post<dynamic>(
            'https://uri-user:uri-password@example.test/profile/private-path',
            queryParameters: {
              'token': 'query-secret',
              'search': 'private-search',
            },
            data: payload,
            options: Options(
              headers: {
                'Authorization': 'Bearer header-secret',
                'X-Person': 'header-person',
              },
              extra: {'trace': 'extra-secret'},
            ),
          )
          .timeout(const Duration(seconds: 3));
      expect(harness.transport.requests.single.data, same(payload));
      expect(
        harness.transport.requests.single.uri.userInfo,
        'uri-user:uri-password',
      );
      expect(
        harness.transport.requests.single.queryParameters['search'],
        'private-search',
      );
      expect(
        harness.transport.requests.single.headers['Authorization'],
        'Bearer header-secret',
      );
      expect(harness.transport.requests.single.extra['trace'], 'extra-secret');
      expect(
        harness.transport.requests.single.extra,
        isNot(contains(TalkerDioLogger.kDioLogsTimeStampKey)),
      );
      expect(
        utf8.decode(harness.transport.sent.single),
        contains('body-password'),
      );
      expect(response.data['profile']['label'], 'response-person');
      expect(response.statusMessage, 'response-status-secret');
      expect(response.headers.value('set-cookie'), 'response-cookie-secret');
      expect(
        response.redirects.single.location.userInfo,
        'redirect-user:redirect-password',
      );
      expect(harness.forwardedResponses.single, same(response));
      expect(
        harness.forwardedRequests.single,
        same(harness.transport.requests.single),
      );
      final logs = harness.output;
      expect(logs, contains('curl -X'));
      expect(logs, contains('https://example.test/'));
      expect(logs, contains('Status: 200'));
      expect(logs, contains('Time:'));
      expect(logs, contains('Redirects:'));
      expect(logs, contains('field_2'));
      _expectHidden(logs, [
        'uri-user',
        'uri-password',
        'private-path',
        'query-secret',
        'private-search',
        'body@example.test',
        'private-label',
        '20123456789',
        'body-password',
        '202400001',
        'header-secret',
        'header-person',
        'extra-secret',
        'response-person',
        'response-cookie-secret',
        'response-status-secret',
        'redirect-user',
        'redirect-password',
        'redirect-private-path',
        'redirect-private-query',
      ]);
      final requestLog = harness.talker.history
          .whereType<DioRequestLog>()
          .single;
      expect(
        requestLog.requestOptions,
        isNot(same(harness.transport.requests.single)),
      );
      expect(requestLog.requestOptions.data, isNot(same(payload)));
      expect(requestLog.requestOptions.cancelToken, isNull);
    },
  );

  test(
    'identifier keys and names never reach captured request response error or form logs',
    () async {
      final harness = _Harness(
        settings: const TalkerDioLoggerSettings(
          printRequestHeaders: true,
          printRequestExtra: true,
          printResponseHeaders: true,
          printErrorHeaders: true,
          hiddenHeaders: {'CONTENT-TYPE'},
        ),
      );
      addTearDown(harness.close);
      final payload = {
        'users': {
          'alice@example.test': {'CredentialKeyABC123': 'key-value-private'},
        },
        'person-key-private': [
          'nested-value-private',
          {'nested-key-private': 20111222333},
        ],
      };
      harness.transport.responseText = jsonEncode({
        'response@example.test': {
          'response-key-private': 'response-value-private',
        },
      });
      harness.transport.responseHeaders['x-response-person-private'] = [
        'response-header-value-private',
        'response-header-second-private',
      ];
      final query = {
        'query@example.test': [
          'query-value-one-private',
          'query-value-two-private',
        ],
      };
      final response = await harness.dio
          .post<dynamic>(
            'https://example.test/keys',
            data: payload,
            queryParameters: query,
            options: Options(
              headers: {
                'x-request-person-private': [
                  'request-header-value-private',
                  'request-header-second-private',
                ],
              },
              extra: {
                'extra@example.test': {
                  'extra-key-private': 'extra-value-private',
                },
              },
            ),
          )
          .timeout(const Duration(seconds: 3));
      expect(harness.transport.requests.single.data, same(payload));
      expect(harness.transport.requests.single.queryParameters, query);
      expect(
        harness.transport.requests.single.headers['x-request-person-private'],
        ['request-header-value-private', 'request-header-second-private'],
      );
      expect(
        harness
            .transport
            .requests
            .single
            .extra['extra@example.test']['extra-key-private'],
        'extra-value-private',
      );
      expect(
        utf8.decode(harness.transport.sent.single),
        contains('alice@example.test'),
      );
      expect(
        response.data['response@example.test']['response-key-private'],
        'response-value-private',
      );
      expect(response.headers['x-response-person-private'], [
        'response-header-value-private',
        'response-header-second-private',
      ]);
      final logged = harness.talker.history
          .whereType<DioRequestLog>()
          .single
          .requestOptions;
      expect((logged.data as Map).length, payload.length);
      expect(
        (logged.data as Map).values.last,
        isA<List>().having((entries) => entries.length, 'length', 2),
      );
      expect(logged.uri.queryParametersAll.values.single.length, 2);
      expect(logged.headers.values.whereType<List>(), hasLength(1));
      expect(logged.headers.values.whereType<List>().single, hasLength(2));
      final loggedResponse = harness.talker.history
          .whereType<DioResponseLog>()
          .single
          .response;
      expect(
        loggedResponse.headers.map.values.where(
          (headers) => headers.length == 2,
        ),
        hasLength(1),
      );
      final form = FormData.fromMap({
        'form@example.test': 'form-value-private',
        'form-json-key-private':
            '{"form-json@example.test":"form-json-value-private"}',
        'file-key-private': MultipartFile.fromBytes(
          utf8.encode('file-bytes-private'),
          filename: 'file-name-private',
        ),
      });
      await harness.dio
          .post<dynamic>('https://example.test/form', data: form)
          .timeout(const Duration(seconds: 3));
      expect(harness.transport.requests.last.data, same(form));
      final multipartBytes = utf8.decode(harness.transport.sent.last);
      expect(multipartBytes, contains('form@example.test'));
      expect(multipartBytes, contains('file-key-private'));
      expect(multipartBytes, contains('file-bytes-private'));
      expect(form.fields.map((entry) => entry.key), [
        'form@example.test',
        'form-json-key-private',
      ]);
      expect(form.files.single.key, 'file-key-private');
      harness.transport.fail = true;
      harness.transport.errorData = {
        'error@example.test': {'error-key-private': 'error-value-private'},
      };
      harness.transport.errorHeaders['x-error-person-private'] = [
        'error-header-value-private',
      ];
      await expectLater(
        harness.dio.get<dynamic>('https://example.test/error'),
        throwsA(
          isA<DioException>()
              .having(
                (error) => error.response!.data,
                'unchanged error payload',
                same(harness.transport.errorData),
              )
              .having(
                (error) =>
                    error.response!.headers.value('x-error-person-private'),
                'unchanged error header',
                'error-header-value-private',
              ),
        ),
      );
      expect(
        harness.forwardedErrors.single,
        same(harness.transport.thrown.single),
      );
      _expectHidden(harness.output, [
        'users',
        'alice@example.test',
        'CredentialKeyABC123',
        'key-value-private',
        'person-key-private',
        'nested-value-private',
        'nested-key-private',
        '20111222333',
        'query@example.test',
        'query-value-one-private',
        'query-value-two-private',
        'x-request-person-private',
        'request-header-value-private',
        'request-header-second-private',
        'extra@example.test',
        'extra-key-private',
        'extra-value-private',
        'response@example.test',
        'response-key-private',
        'response-value-private',
        'x-response-person-private',
        'response-header-value-private',
        'response-header-second-private',
        'form@example.test',
        'form-value-private',
        'form-json-key-private',
        'form-json@example.test',
        'form-json-value-private',
        'file-key-private',
        'file-name-private',
        'file-bytes-private',
        'error@example.test',
        'error-key-private',
        'error-value-private',
        'x-error-person-private',
        'error-header-value-private',
      ]);
      expect(harness.output, isNot(contains('application/json')));
      expect(harness.output, contains('field_1'));
      expect(harness.output, contains('file_1=@[FILE]'));
    },
  );

  test(
    'error logs redact payload and exception while forwarding the same live error',
    () async {
      final harness = _Harness();
      addTearDown(harness.close);
      harness.transport.fail = true;
      for (var iteration = 0; iteration < 8; iteration++) {
        try {
          await harness.dio
              .get<dynamic>(
                'https://example.test/fail',
                queryParameters: {'email': 'error-query-person'},
              )
              .timeout(const Duration(seconds: 3));
          fail('The transport error must reach the caller');
        } on DioException catch (error) {
          expect(error, same(harness.transport.thrown.last));
          expect(harness.forwardedErrors.last, same(error));
          expect(error.message, 'exception-message-secret');
          expect(error.error, 'underlying-error-secret');
          expect(error.response!.data['detail'], 'error-body-person');
        }
      }
      expect(harness.talker.history.whereType<DioErrorLog>(), hasLength(8));
      expect(harness.output, contains('Status: 422'));
      _expectHidden(harness.output, [
        'error-query-person',
        'exception-message-secret',
        'underlying-error-secret',
        'error-body-person',
        'error-cookie-secret',
        'stack-secret',
      ]);
      final logged = harness.talker.history
          .whereType<DioErrorLog>()
          .first
          .dioException;
      expect(logged.error, isNull);
      expect(logged.stackTrace.toString(), isEmpty);
    },
  );

  for (final convertFormData in [true, false]) {
    test(
      'multipart transport stays intact with convertFormData=$convertFormData',
      () async {
        final harness = _Harness(
          convertFormData: convertFormData,
          settings: const TalkerDioLoggerSettings(printRequestHeaders: true),
        );
        addTearDown(harness.close);
        final form = FormData.fromMap({
          'profile': '{"email":"form-person@example.test"}',
          'note': 'form-note-secret',
          'attachment': MultipartFile.fromBytes(
            utf8.encode('file-content-secret'),
            filename: 'private-filename.txt',
          ),
        });
        await harness.dio
            .post<dynamic>('https://example.test/upload', data: form)
            .timeout(const Duration(seconds: 3));
        expect(harness.transport.requests.single.data, same(form));
        final transmitted = utf8.decode(harness.transport.sent.single);
        expect(transmitted, contains('form-person@example.test'));
        expect(transmitted, contains('file-content-secret'));
        expect(transmitted, contains('private-filename.txt'));
        _expectHidden(harness.output, [
          'form-person@example.test',
          'form-note-secret',
          'file-content-secret',
          'private-filename.txt',
        ]);
        expect(
          harness.output,
          contains(convertFormData ? 'file_1' : '[FORM DATA]'),
        );
        final curl = harness.talker.history
            .firstWhere((entry) => entry.message?.startsWith('curl ') ?? false)
            .message!;
        expect(curl, isNot(contains('--data-raw')));
        expect(curl, isNot(contains(form.boundary)));
        expect(curl, isNot(contains('content-type:')));
        if (convertFormData) {
          expect(curl, contains('-F'));
          expect(curl, contains('file_1=@[FILE]'));
        } else {
          expect(curl, isNot(contains('-F')));
        }
      },
    );
  }

  test(
    'disabled and filtered logging leaves original routing decisions and payloads intact',
    () async {
      var disabledCalls = 0;
      final disabled = _Harness(
        settings: TalkerDioLoggerSettings(
          enabled: false,
          requestFilter: (_) {
            disabledCalls++;
            return true;
          },
        ),
      );
      addTearDown(disabled.close);
      await disabled.dio.get<dynamic>('https://example.test/health');
      expect(disabled.talker.history, isEmpty);
      expect(disabledCalls, 0);
      final decisions = <String>[];
      final filtered = _Harness(
        settings: TalkerDioLoggerSettings(
          requestFilter: (request) {
            decisions.add(
              'request:${request.path}:${request.queryParameters['token']}',
            );
            return !request.path.endsWith('/health');
          },
          responseFilter: (response) {
            decisions.add('response:${response.data['profile']['label']}');
            return false;
          },
          errorFilter: (error) {
            decisions.add('error:${error.message}');
            return false;
          },
        ),
      );
      addTearDown(filtered.close);
      await filtered.dio.get<dynamic>(
        'https://example.test/health',
        queryParameters: {'token': 'filter-secret'},
      );
      filtered.transport.fail = true;
      await expectLater(
        filtered.dio.get<dynamic>(
          'https://example.test/health',
          queryParameters: {'token': 'filter-secret'},
        ),
        throwsA(isA<DioException>()),
      );
      expect(filtered.talker.history, isEmpty);
      expect(decisions, [
        'request:https://example.test/health:filter-secret',
        'response:response-person',
        'request:https://example.test/health:filter-secret',
        'error:exception-message-secret',
      ]);
    },
  );

  test(
    'settings suppress cURL fields and converters only receive independent safe copies',
    () async {
      Response<dynamic>? converted;
      final harness = _Harness(
        settings: TalkerDioLoggerSettings(
          logLevel: LogLevel.warning,
          printRequestData: false,
          printRequestHeaders: false,
          printRequestExtra: false,
          printResponseHeaders: false,
          printResponseMessage: false,
          jsonFormatter: TalkerJsonFormatter.custom(
            (payload) => jsonEncode(payload),
          ),
          responseDataConverter: (response) {
            converted = response;
            return 'converted:${jsonEncode(response.data)}';
          },
        ),
      );
      addTearDown(harness.close);
      final original = await harness.dio.post<dynamic>(
        'https://example.test/items',
        data: {'requestField': 'request-private'},
        options: Options(
          headers: {'X-Private': 'header-private'},
          extra: {'extraField': 'extra-private'},
        ),
      );
      expect(converted, isNot(same(original)));
      expect(converted!.data, isNot(same(original.data)));
      expect(jsonEncode(converted!.data), isNot(contains('response-person')));
      expect(harness.output, contains('converted:'));
      expect(harness.output, isNot(contains('requestField')));
      expect(harness.output, isNot(contains('X-Private')));
      expect(harness.output, isNot(contains('extraField')));
      final requestText = harness.talker.history
          .whereType<DioRequestLog>()
          .single
          .generateTextMessage();
      for (final section in ['Data:', 'Headers:', 'Extra:']) {
        expect(requestText, isNot(contains(section)));
      }
      final curl = harness.talker.history
          .firstWhere((entry) => entry.message?.startsWith('curl ') ?? false)
          .message!;
      expect(curl, isNot(contains('--data-raw')));
      expect(curl, isNot(contains(' -H ')));

      expect(harness.output, isNot(contains('Message:')));
      expect(
        harness.talker.history.whereType<DioRequestLog>().single.logLevel,
        LogLevel.warning,
      );
      expect(harness.talker.history.first.logLevel, LogLevel.warning);
    },
  );

  test(
    'response and HTTP error switches suppress all optional payload sections',
    () async {
      var converterCalls = 0;
      final harness = _Harness(
        settings: TalkerDioLoggerSettings(
          printResponseData: false,
          printResponseHeaders: false,
          printResponseMessage: false,
          printErrorData: false,
          printErrorHeaders: false,
          printErrorMessage: false,
          responseDataConverter: (_) {
            converterCalls++;
            return 'unexpected';
          },
        ),
      );
      addTearDown(harness.close);
      await harness.dio.get<dynamic>('https://example.test/success');
      harness.transport.badStatus = true;
      await expectLater(
        harness.dio.get<dynamic>('https://example.test/fail'),
        throwsA(
          isA<DioException>()
              .having((error) => error.response!.statusCode, 'status', 422)
              .having(
                (error) => error.response!.data['profile']['label'],
                'original body',
                'response-person',
              ),
        ),
      );
      final phaseLogs = harness.talker.history
          .where((entry) => entry is DioResponseLog || entry is DioErrorLog)
          .map((entry) => entry.generateTextMessage())
          .join('\n');
      expect(phaseLogs, contains('Status: 200'));
      expect(phaseLogs, contains('Status: 422'));
      for (final section in [
        'Data:',
        'Headers:',
        'Message:',
        'Redirects:',
        'Time:',
      ]) {
        expect(phaseLogs, isNot(contains(section)));
      }
      expect(converterCalls, 0);
    },
  );

  test(
    'hidden media headers stay hidden and JSON formatters receive only safe copies',
    () async {
      final formatted = <String>[];
      final harness = _Harness(
        settings: TalkerDioLoggerSettings(
          printRequestHeaders: true,
          printResponseHeaders: true,
          hiddenHeaders: {'CONTENT-TYPE'},
          jsonFormatter: TalkerJsonFormatter.custom((payload) {
            final encoded = jsonEncode(payload);
            formatted.add(encoded);
            return 'formatted:$encoded';
          }),
        ),
      );
      addTearDown(harness.close);
      await harness.dio.post<dynamic>(
        'https://example.test/items',
        data: {'password': 'formatter-private'},
      );
      final logs = harness.output;
      expect(logs, contains('formatted:'));
      expect(formatted, isNotEmpty);
      _expectHidden(formatted.join('\n'), [
        'formatter-private',
        'response-person',
        'response-cookie-secret',
      ]);
      expect(logs, isNot(contains('application/json')));
      expect(harness.transport.requests.single.contentType, 'application/json');
      harness.dio.interceptors
          .whereType<AppInterceptorLogger>()
          .single
          .settings = const TalkerDioLoggerSettings(
        enabled: false,
      );
      final logCount = harness.talker.history.length;
      await harness.dio.get<dynamic>('https://example.test/disabled');
      expect(harness.talker.history.length, logCount);
    },
  );

  test(
    'opaque text and stream bodies are not consumed or exposed by logging',
    () async {
      for (final body in <Object>[
        'opaque-text-private',
        '{"label":"json-text-private"}',
        Stream<List<int>>.value(utf8.encode('stream-private')),
      ]) {
        final harness = _Harness();
        addTearDown(harness.close);
        harness.transport.responseText = 'opaque-response-private';
        final response = await harness.dio
            .post<dynamic>(
              'https://example.test/raw',
              data: body,
              options: Options(
                contentType: 'application/octet-stream',
                responseType: ResponseType.plain,
              ),
            )
            .timeout(const Duration(seconds: 3));
        expect(response.data, 'opaque-response-private');
        expect(harness.transport.requests.single.data, same(body));
        expect(harness.transport.sent.single, isNotEmpty);
        _expectHidden(harness.output, [
          'opaque-text-private',
          'json-text-private',
          'stream-private',
          'opaque-response-private',
        ]);
      }
    },
  );
}

void _expectHidden(String logs, List<String> secrets) {
  for (final secret in secrets) {
    expect(logs, isNot(contains(secret)), reason: 'Exposed $secret');
  }
}

class _Harness {
  _Harness({
    TalkerDioLoggerSettings settings = const TalkerDioLoggerSettings(),
    bool convertFormData = true,
  }) {
    dio.httpClientAdapter = transport;
    dio.interceptors.add(
      AppInterceptorLogger(
        talker: talker,
        settings: settings,
        convertFormData: convertFormData,
      ),
    );
    dio.interceptors.add(
      InterceptorsWrapper(
        onRequest: (request, handler) {
          forwardedRequests.add(request);
          handler.next(request);
        },
        onResponse: (response, handler) {
          forwardedResponses.add(response);
          handler.next(response);
        },
        onError: (error, handler) {
          forwardedErrors.add(error);
          handler.next(error);
        },
      ),
    );
  }

  final dio = Dio();
  final transport = _Transport();
  final talker = Talker(settings: TalkerSettings(useConsoleLogs: false));
  final forwardedRequests = <RequestOptions>[];
  final forwardedResponses = <Response<dynamic>>[];
  final forwardedErrors = <DioException>[];

  String get output =>
      talker.history.map((entry) => entry.generateTextMessage()).join('\n');
  void close() => dio.close(force: true);
}

class _Transport implements HttpClientAdapter {
  final requests = <RequestOptions>[];
  final sent = <List<int>>[];
  final thrown = <DioException>[];
  bool fail = false;
  bool badStatus = false;
  String? responseText;
  Object? errorData;
  final responseHeaders = <String, List<String>>{
    'content-type': ['application/json'],
    'set-cookie': ['response-cookie-secret'],
  };
  final errorHeaders = <String, List<String>>{
    'set-cookie': ['error-cookie-secret'],
  };

  @override
  Future<ResponseBody> fetch(
    RequestOptions options,
    Stream<Uint8List>? requestStream,
    Future<void>? cancelFuture,
  ) async {
    requests.add(options);
    final bytes = <int>[];
    if (requestStream != null) {
      await for (final chunk in requestStream) {
        bytes.addAll(chunk);
      }
    }
    sent.add(bytes);
    if (fail) {
      final error = DioException(
        requestOptions: options,
        type: DioExceptionType.badResponse,
        message: 'exception-message-secret',
        error: 'underlying-error-secret',
        stackTrace: StackTrace.fromString('stack-secret'),
        response: Response<dynamic>(
          requestOptions: options,
          statusCode: 422,
          data: errorData ?? {'detail': 'error-body-person'},
          headers: Headers.fromMap(errorHeaders),
        ),
      );
      thrown.add(error);
      throw error;
    }
    return ResponseBody(
      Stream.value(
        Uint8List.fromList(
          utf8.encode(
            responseText ??
                jsonEncode({
                  'profile': {'label': 'response-person'},
                }),
          ),
        ),
      ),
      badStatus ? 422 : 200,
      isRedirect: true,
      redirects: [
        RedirectRecord(
          307,
          'GET',
          Uri.parse(
            'https://redirect-user:redirect-password@example.test/redirect-private-path?search=redirect-private-query',
          ),
        ),
      ],
      statusMessage: 'response-status-secret',
      headers: responseHeaders,
    );
  }

  @override
  void close({bool force = false}) {}
}
