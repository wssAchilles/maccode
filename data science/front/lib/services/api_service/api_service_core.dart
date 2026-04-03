part of '../api_service.dart';

const String _defaultTimeoutError = '请求超时，请稍后重试';

http.Client _httpClient = http.Client();
Future<String?> Function()? _tokenProviderOverride;

String get _baseUrl => AppConstants.apiBaseUrl;
String get _heavyBaseUrl => AppConstants.heavyApiBaseUrl;

Future<http.Response> _requestWithTimeout(
  Future<http.Response> request, {
  Duration? timeout,
  String timeoutMessage = _defaultTimeoutError,
}) async {
  try {
    return await request.timeout(
      timeout ?? AppConstants.apiTimeout,
      onTimeout: () => throw ApiServiceException(
        timeoutMessage,
        kind: ApiServiceErrorKind.timeout,
      ),
    );
  } on http.ClientException catch (exc) {
    throw ApiServiceException(
      '网络请求失败，请检查浏览器网络、跨域配置或后端服务状态',
      kind: ApiServiceErrorKind.server,
      body: exc.message,
    );
  } catch (exc) {
    final message = exc.toString();
    if (message.contains('Failed to fetch')) {
      throw ApiServiceException(
        '网络请求失败，请检查浏览器网络、跨域配置或后端服务状态',
        kind: ApiServiceErrorKind.server,
        body: message,
      );
    }
    rethrow;
  }
}

Uri _buildUri(
  String baseUrl,
  String path, {
  Map<String, Object?>? queryParameters,
}) {
  final filtered = <String, String>{};

  queryParameters?.forEach((key, value) {
    if (value != null) {
      filtered[key] = value.toString();
    }
  });

  return Uri.parse(
    '$baseUrl$path',
  ).replace(queryParameters: filtered.isEmpty ? null : filtered);
}

Future<Map<String, String>> _getAuthHeaders() async {
  String? token;

  if (_tokenProviderOverride != null) {
    token = await _tokenProviderOverride!();
  } else {
    final user = FirebaseAuth.instance.currentUser;
    if (user == null) {
      throw const ApiServiceException(
        'User not authenticated',
        kind: ApiServiceErrorKind.unauthenticated,
      );
    }
    token = await user.getIdToken();
  }

  if (token == null || token.isEmpty) {
    throw const ApiServiceException(
      'User not authenticated',
      kind: ApiServiceErrorKind.unauthenticated,
    );
  }

  return <String, String>{
    'Content-Type': 'application/json',
    'Authorization': 'Bearer $token',
  };
}

Future<http.Response> _authorizedGet(
  String baseUrl,
  String path, {
  Map<String, Object?>? queryParameters,
  Duration? timeout,
  String timeoutMessage = _defaultTimeoutError,
}) async {
  final headers = await _getAuthHeaders();
  return _requestWithTimeout(
    _httpClient.get(
      _buildUri(baseUrl, path, queryParameters: queryParameters),
      headers: headers,
    ),
    timeout: timeout,
    timeoutMessage: timeoutMessage,
  );
}

Future<http.Response> _authorizedPost(
  String baseUrl,
  String path, {
  Object? body,
  Map<String, Object?>? queryParameters,
  Duration? timeout,
  String timeoutMessage = _defaultTimeoutError,
  Map<String, String>? headers,
}) async {
  final authHeaders = headers ?? await _getAuthHeaders();
  return _requestWithTimeout(
    _httpClient.post(
      _buildUri(baseUrl, path, queryParameters: queryParameters),
      headers: authHeaders,
      body: body,
    ),
    timeout: timeout,
    timeoutMessage: timeoutMessage,
  );
}

Future<http.Response> _authorizedPatch(
  String baseUrl,
  String path, {
  Object? body,
  Map<String, Object?>? queryParameters,
  Duration? timeout,
  String timeoutMessage = _defaultTimeoutError,
  Map<String, String>? headers,
}) async {
  final authHeaders = headers ?? await _getAuthHeaders();
  return _requestWithTimeout(
    _httpClient.patch(
      _buildUri(baseUrl, path, queryParameters: queryParameters),
      headers: authHeaders,
      body: body,
    ),
    timeout: timeout,
    timeoutMessage: timeoutMessage,
  );
}

Future<http.Response> _authorizedDelete(
  String baseUrl,
  String path, {
  Map<String, Object?>? queryParameters,
  Duration? timeout,
  String timeoutMessage = _defaultTimeoutError,
}) async {
  final headers = await _getAuthHeaders();
  return _requestWithTimeout(
    _httpClient.delete(
      _buildUri(baseUrl, path, queryParameters: queryParameters),
      headers: headers,
    ),
    timeout: timeout,
    timeoutMessage: timeoutMessage,
  );
}

Future<http.Response> _publicGet(
  String baseUrl,
  String path, {
  Map<String, Object?>? queryParameters,
  Duration? timeout,
  String timeoutMessage = _defaultTimeoutError,
}) {
  return _requestWithTimeout(
    _httpClient.get(_buildUri(baseUrl, path, queryParameters: queryParameters)),
    timeout: timeout,
    timeoutMessage: timeoutMessage,
  );
}

Map<String, dynamic> _decodeJsonMap(
  String body, {
  String failureMessage = '响应数据格式错误',
}) {
  try {
    final decoded = jsonDecode(body);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    if (decoded is Map) {
      return Map<String, dynamic>.from(decoded);
    }
    throw const FormatException('Expected a JSON object.');
  } on FormatException {
    throw ApiServiceException(
      failureMessage,
      kind: ApiServiceErrorKind.badResponse,
      body: body,
    );
  }
}

Map<String, dynamic>? _tryDecodeJsonMap(String body) {
  try {
    final decoded = jsonDecode(body);
    if (decoded is Map<String, dynamic>) {
      return decoded;
    }
    if (decoded is Map) {
      return Map<String, dynamic>.from(decoded);
    }
    return null;
  } catch (_) {
    return null;
  }
}

bool _isSuccessStatus(int statusCode) {
  return statusCode >= 200 && statusCode < 300;
}

String? _extractPayloadMessage(Map<String, dynamic>? data) {
  final dynamic directMessage = data?['message'] ?? data?['detail'];
  if (directMessage is String && directMessage.trim().isNotEmpty) {
    return directMessage.trim();
  }

  final dynamic error = data?['error'];
  if (error is String && error.trim().isNotEmpty) {
    return error.trim();
  }
  if (error is Map) {
    final nestedMessage = error['message'];
    if (nestedMessage is String && nestedMessage.trim().isNotEmpty) {
      return nestedMessage.trim();
    }
  }
  return null;
}

String _buildFailureMessage({
  required String fallback,
  required int statusCode,
  String? detail,
  String? rawBody,
}) {
  if (detail != null && detail.isNotEmpty) {
    return detail == fallback ? fallback : '$fallback: $detail';
  }

  final trimmedBody = rawBody?.trim();
  if (trimmedBody != null && trimmedBody.isNotEmpty) {
    return '$fallback: $trimmedBody';
  }

  return '$fallback: HTTP $statusCode';
}

Never _throwResponseException(
  http.Response response, {
  required String fallback,
}) {
  final data = _tryDecodeJsonMap(response.body);
  throw ApiServiceException(
    _buildFailureMessage(
      fallback: fallback,
      statusCode: response.statusCode,
      detail: _extractPayloadMessage(data),
      rawBody: data == null ? response.body : null,
    ),
    statusCode: response.statusCode,
    kind: ApiServiceErrorKind.server,
    body: response.body,
  );
}

Map<String, dynamic> _decodeResponseMap(
  http.Response response, {
  required String fallback,
  bool requireSuccessFlag = false,
}) {
  if (!_isSuccessStatus(response.statusCode)) {
    _throwResponseException(response, fallback: fallback);
  }

  final data = _decodeJsonMap(
    response.body,
    failureMessage: '$fallback: 响应数据格式错误',
  );

  if (requireSuccessFlag && data['success'] != true) {
    throw ApiServiceException(
      _buildFailureMessage(
        fallback: fallback,
        statusCode: response.statusCode,
        detail: _extractPayloadMessage(data),
      ),
      statusCode: response.statusCode,
      kind: ApiServiceErrorKind.server,
      body: response.body,
    );
  }

  return data;
}

bool _containsLicenseIssue(String? value) {
  return value != null && value.toLowerCase().contains('license');
}

String _formatDate(DateTime date) {
  return '${date.year}-${date.month.toString().padLeft(2, '0')}-${date.day.toString().padLeft(2, '0')}';
}
