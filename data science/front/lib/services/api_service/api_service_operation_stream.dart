part of '../api_service.dart';

Stream<JobStreamFrame> _streamOperation(
  String operationId, {
  double pollInterval = 2.0,
  double maxDuration = 55.0,
}) async* {
  final headers = await _getAuthHeaders();
  final request = http.Request(
    'GET',
    _buildUri(
      _baseUrl,
      '/api/operations/$operationId/stream',
      queryParameters: <String, Object?>{
        'poll_interval': pollInterval,
        'max_duration': maxDuration,
      },
    ),
  );
  request.headers.addAll(headers);
  request.headers['Accept'] = 'text/event-stream';

  http.StreamedResponse response;
  try {
    response = await _httpClient
        .send(request)
        .timeout(
          AppConstants.connectTimeout,
          onTimeout: () => throw const ApiServiceException(
            '任务流连接超时，请稍后重试',
            kind: ApiServiceErrorKind.timeout,
          ),
        );
  } on http.ClientException catch (exc) {
    throw ApiServiceException(
      '任务流连接失败，请检查网络或后端服务状态',
      kind: ApiServiceErrorKind.server,
      body: exc.message,
    );
  }

  if (!_isSuccessStatus(response.statusCode)) {
    final body = await response.stream.bytesToString();
    final payload = _tryDecodeJsonMap(body);
    throw ApiServiceException(
      _extractPayloadMessage(payload) ?? '任务流订阅失败',
      statusCode: response.statusCode,
      kind: response.statusCode == 401 || response.statusCode == 403
          ? ApiServiceErrorKind.unauthenticated
          : ApiServiceErrorKind.server,
      body: body,
    );
  }

  yield* parseOperationSse(response.stream);
}
