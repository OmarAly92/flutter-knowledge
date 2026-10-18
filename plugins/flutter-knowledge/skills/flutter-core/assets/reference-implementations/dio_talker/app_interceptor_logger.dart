import 'dart:convert';

import 'package:dio/dio.dart';
import 'package:talker/talker.dart';
import 'package:talker_dio_logger/talker_dio_logger.dart';

class AppInterceptorLogger extends TalkerDioLogger {
  AppInterceptorLogger({
    required Talker talker,
    super.settings = const TalkerDioLoggerSettings(),
    this.convertFormData = true,
  }) : _talker = talker,
       super(talker: talker);

  final Talker _talker;
  final bool convertFormData;
  final _requests = Expando<RequestOptions>();

  static const _redacted = '[REDACTED]';
  static const _debug =
      !bool.fromEnvironment('dart.vm.product') &&
      !bool.fromEnvironment('dart.vm.profile');

  @override
  void onRequest(RequestOptions options, RequestInterceptorHandler handler) {
    if (!_debug || !settings.enabled) {
      handler.next(options);
      return;
    }
    final safe = _request(options);
    _requests[options] = safe;
    if (settings.printResponseTime) {
      safe.extra[TalkerDioLogger.kDioLogsTimeStampKey] =
          DateTime.now().millisecondsSinceEpoch;
    }
    if (!(settings.requestFilter?.call(options) ?? true)) {
      handler.next(options);
      return;
    }
    _log(() {
      super.onRequest(safe, _RequestForwarder(options, handler));
      _talker.log(
        options.data is FormData ? _formCurl(safe) : _curl(safe),
        logLevel: settings.logLevel,
      );
    });
  }

  @override
  void onResponse(Response response, ResponseInterceptorHandler handler) {
    if (!_debug ||
        !settings.enabled ||
        !(settings.responseFilter?.call(response) ?? true)) {
      handler.next(response);
      return;
    }
    _log(
      () => super.onResponse(
        _response(response),
        _ResponseForwarder(response, handler),
      ),
    );
  }

  @override
  void onError(DioException err, ErrorInterceptorHandler handler) {
    if (!_debug ||
        !settings.enabled ||
        !(settings.errorFilter?.call(err) ?? true)) {
      handler.next(err);
      return;
    }
    final safe = DioException(
      requestOptions:
          _requests[err.requestOptions] ?? _request(err.requestOptions),
      response: err.response == null ? null : _response(err.response!),
      type: err.type,
      message: err.type.name,
      stackTrace: StackTrace.fromString(''),
    );
    _log(() => super.onError(safe, _ErrorForwarder(err, handler)));
  }

  void _log(void Function() write) {
    final configured = settings;
    settings = _withoutFilters(configured);
    try {
      write();
    } finally {
      settings = configured;
    }
  }

  TalkerDioLoggerSettings _withoutFilters(TalkerDioLoggerSettings configured) =>
      TalkerDioLoggerSettings(
        enabled: configured.enabled,
        logLevel: configured.logLevel,
        printRequestData: configured.printRequestData,
        printRequestHeaders: configured.printRequestHeaders,
        printRequestExtra: configured.printRequestExtra,
        printResponseData: configured.printResponseData,
        printResponseHeaders: configured.printResponseHeaders,
        printResponseMessage: configured.printResponseMessage,
        printResponseRedirects: configured.printResponseRedirects,
        printResponseTime: configured.printResponseTime,
        printErrorData: configured.printErrorData,
        printErrorHeaders: configured.printErrorHeaders,
        printErrorMessage: configured.printErrorMessage,
        hiddenHeaders: configured.hiddenHeaders,
        jsonFormatter: configured.jsonFormatter,
        responseDataConverter: configured.responseDataConverter,
        requestPen: configured.requestPen,
        responsePen: configured.responsePen,
        errorPen: configured.errorPen,
      );

  RequestOptions _request(RequestOptions original) => RequestOptions(
    path: _uri(original.uri).toString(),
    method: _method(original.method),
    data: _payload(original.data),
    headers: _headers(original.headers),
    extra: _map(original.extra, 0),
    sourceStackTrace: StackTrace.empty,
  );

  Response<dynamic> _response(Response original) => Response<dynamic>(
    requestOptions:
        _requests[original.requestOptions] ?? _request(original.requestOptions),
    data: _payload(original.data),
    statusCode: original.statusCode,
    statusMessage: original.statusMessage == null ? null : _redacted,
    headers: Headers.fromMap(
      _headers(
        original.headers.map,
      ).map((key, header) => MapEntry(key, header as List<String>)),
    ),
    extra: _map(original.extra, 0),
    isRedirect: original.isRedirect,
    redirects: original.redirects
        .map(
          (redirect) => RedirectRecord(
            redirect.statusCode,
            _method(redirect.method),
            _uri(redirect.location),
          ),
        )
        .toList(),
  );

  Uri _uri(Uri original) => original.replace(
    userInfo: '',
    fragment: '',
    pathSegments: original.pathSegments.map(
      (segment) => segment.isEmpty ? '' : _redacted,
    ),
    queryParameters: {
      for (final (index, values) in original.queryParametersAll.values.indexed)
        'query_${index + 1}': List.filled(values.length, _redacted),
    },
  );

  String _method(String original) =>
      const {
        'GET',
        'HEAD',
        'POST',
        'PUT',
        'PATCH',
        'DELETE',
        'OPTIONS',
        'TRACE',
        'CONNECT',
      }.contains(original.toUpperCase())
      ? original.toUpperCase()
      : 'CUSTOM';

  Map<String, dynamic> _headers(Map<String, dynamic> original) {
    final safe = <String, dynamic>{};
    for (final (index, entry) in original.entries.indexed) {
      final protocolName = entry.key.toLowerCase();
      final name =
          const {'accept', 'content-type'}.contains(protocolName) &&
              !safe.containsKey(protocolName)
          ? protocolName
          : 'header-${index + 1}';
      safe[name] = entry.value is List
          ? [
              for (final header in entry.value as List)
                _header(entry.key, header),
            ]
          : _header(entry.key, entry.value);
    }
    return safe;
  }

  String _header(String key, Object? header) {
    if (settings.hiddenHeaders.any(
      (hidden) => hidden.toLowerCase() == key.toLowerCase(),
    )) {
      return _redacted;
    }
    if (header is String &&
        const {'accept', 'content-type'}.contains(key.toLowerCase())) {
      final mediaType = header.split(';').first.trim().toLowerCase();
      if (const {
        'application/json',
        'application/octet-stream',
        'application/x-www-form-urlencoded',
        'multipart/form-data',
        'text/plain',
      }.contains(mediaType))
        return mediaType;
    }
    return _redacted;
  }

  Object? _payload(Object? original, [int depth = 0]) {
    if (original == null) return null;
    if (depth >= 8) return _redacted;
    if (original is Map) return _map(original, depth);
    if (original is List)
      return original.map((entry) => _payload(entry, depth + 1)).toList();
    if (original is FormData) {
      if (!convertFormData) return '[FORM DATA]';
      return {
        'fields': [
          for (final (index, field) in original.fields.indexed)
            {'field_${index + 1}': _payload(field.value, depth + 1)},
        ],
        'files': [
          for (final (index, _) in original.files.indexed)
            {'file_${index + 1}': '[FILE]'},
        ],
      };
    }
    if (original is String) {
      try {
        final decoded = jsonDecode(original);
        if (decoded is Map || decoded is List)
          return _payload(decoded, depth + 1);
      } on FormatException {
        return _redacted;
      }
    }
    return _redacted;
  }

  Map<String, dynamic> _map(Map original, int depth) => {
    for (final (index, entry) in original.entries.indexed)
      'field_${index + 1}': _payload(entry.value, depth + 1),
  };

  String _quote(Object? argument) =>
      "'${argument.toString().replaceAll("'", "'\\''")}'";

  List<String> _curlHead(RequestOptions safe, Map<String, dynamic> headers) {
    final arguments = ['curl', '-X', _quote(safe.method), _quote(safe.uri)];
    if (settings.printRequestHeaders) {
      for (final header in headers.entries) {
        arguments.addAll(['-H', _quote('${header.key}: ${header.value}')]);
      }
    }
    return arguments;
  }

  String _curl(RequestOptions safe) {
    final arguments = _curlHead(safe, safe.headers);
    if (settings.printRequestData && safe.data != null) {
      arguments.addAll(['--data-raw', _quote(jsonEncode(safe.data))]);
    }
    return arguments.join(' ');
  }

  String _formCurl(RequestOptions safe) {
    final headers = Map<String, dynamic>.of(safe.headers)
      ..removeWhere((key, _) => key.toLowerCase() == 'content-type');
    final arguments = _curlHead(safe, headers);
    if (settings.printRequestData && convertFormData) {
      final form = safe.data as Map;
      for (final field in form['fields'] as List) {
        final entry = (field as Map).entries.single;
        arguments.addAll([
          '-F',
          _quote('${entry.key}=${jsonEncode(entry.value)}'),
        ]);
      }
      for (final file in form['files'] as List) {
        arguments.addAll([
          '-F',
          _quote('${(file as Map).keys.single}=@[FILE]'),
        ]);
      }
    }
    return arguments.join(' ');
  }
}

class _RequestForwarder extends RequestInterceptorHandler {
  _RequestForwarder(this.original, this.target);
  final RequestOptions original;
  final RequestInterceptorHandler target;

  @override
  void next(RequestOptions requestOptions) => target.next(original);
}

class _ResponseForwarder extends ResponseInterceptorHandler {
  _ResponseForwarder(this.original, this.target);
  final Response original;
  final ResponseInterceptorHandler target;

  @override
  void next(Response response) => target.next(original);
}

class _ErrorForwarder extends ErrorInterceptorHandler {
  _ErrorForwarder(this.original, this.target);
  final DioException original;
  final ErrorInterceptorHandler target;

  @override
  void next(DioException error) => target.next(original);
}
