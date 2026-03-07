part of '../api_service.dart';

Future<OptimizationResponse> _runOptimization({
  double initialSoc = AppConstants.defaultInitialSoc,
  DateTime? targetDate,
  List<double>? temperatureForecast,
  double? temperatureAdjust,
  double? batteryCapacity,
  double? batteryPower,
  double? batteryEfficiency,
}) async {
  if (initialSoc < AppConstants.minSoc || initialSoc > AppConstants.maxSoc) {
    throw ArgumentError(
      'initialSoc must be between ${AppConstants.minSoc} and ${AppConstants.maxSoc}',
    );
  }

  if (temperatureForecast != null && temperatureForecast.length != 24) {
    throw ArgumentError('temperatureForecast must contain exactly 24 values');
  }

  final response = await _authorizedPost(
    _baseUrl,
    '/api/optimization/run',
    body: jsonEncode(<String, dynamic>{
      'initial_soc': initialSoc,
      if (targetDate != null) 'target_date': _formatDate(targetDate),
      if (temperatureForecast != null)
        'temperature_forecast': temperatureForecast,
      if (temperatureAdjust != null) 'temperature_adjust': temperatureAdjust,
      if (batteryCapacity != null) 'battery_capacity': batteryCapacity,
      if (batteryPower != null) 'battery_power': batteryPower,
      if (batteryEfficiency != null) 'battery_efficiency': batteryEfficiency,
    }),
    timeout: AppConstants.optimizationTimeout,
    timeoutMessage: '优化请求超时，请稍后重试',
  );

  if (_isSuccessStatus(response.statusCode)) {
    final data = _decodeJsonMap(response.body, failureMessage: '响应数据格式错误');
    try {
      return OptimizationResponse.fromJson(data);
    } on FormatException catch (e) {
      throw ApiServiceException(
        '响应数据格式错误: ${e.message}',
        kind: ApiServiceErrorKind.badResponse,
        body: response.body,
      );
    }
  }

  final data = _tryDecodeJsonMap(response.body);
  final detail = _extractPayloadMessage(data);
  final errorText = '${detail ?? ''} ${response.body}'.trim();

  switch (response.statusCode) {
    case 401:
      throw ApiServiceException(
        _buildFailureMessage(
          fallback: AppConstants.authError,
          statusCode: response.statusCode,
          detail: detail,
          rawBody: data == null ? response.body : null,
        ),
        statusCode: 401,
        kind: ApiServiceErrorKind.unauthenticated,
        body: response.body,
      );
    case 400:
      throw ApiServiceException(
        _buildFailureMessage(
          fallback: '请求参数错误',
          statusCode: response.statusCode,
          detail: detail,
          rawBody: data == null ? response.body : null,
        ),
        statusCode: 400,
        kind: ApiServiceErrorKind.server,
        body: response.body,
      );
    case 404:
      throw ApiServiceException(
        _buildFailureMessage(
          fallback: '预测模型未找到，请联系管理员',
          statusCode: response.statusCode,
          detail: detail,
          rawBody: data == null ? response.body : null,
        ),
        statusCode: 404,
        kind: ApiServiceErrorKind.server,
        body: response.body,
      );
    case 500:
      if (_containsLicenseIssue(errorText)) {
        throw const ApiServiceException(
          '优化服务暂时不可用 (许可证错误)',
          statusCode: 500,
          kind: ApiServiceErrorKind.server,
        );
      }
      throw ApiServiceException(
        _buildFailureMessage(
          fallback: AppConstants.serverError,
          statusCode: response.statusCode,
          detail: detail,
          rawBody: data == null ? response.body : null,
        ),
        statusCode: 500,
        kind: ApiServiceErrorKind.server,
        body: response.body,
      );
    default:
      throw ApiServiceException(
        _buildFailureMessage(
          fallback: '优化失败',
          statusCode: response.statusCode,
          detail: detail,
          rawBody: data == null ? response.body : null,
        ),
        statusCode: response.statusCode,
        kind: ApiServiceErrorKind.server,
        body: response.body,
      );
  }
}

Future<Map<String, dynamic>> _getOptimizationConfig() async {
  final response = await _publicGet(_baseUrl, '/api/optimization/config');
  return _decodeResponseMap(
    response,
    fallback: 'Failed to get config',
    requireSuccessFlag: true,
  );
}

Future<Map<String, dynamic>> _simulateScenarios({
  DateTime? targetDate,
  List<Map<String, dynamic>>? scenarios,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/optimization/simulate',
    body: jsonEncode(<String, dynamic>{
      if (targetDate != null) 'target_date': _formatDate(targetDate),
      if (scenarios != null) 'scenarios': scenarios,
    }),
    timeout: AppConstants.optimizationTimeout,
    timeoutMessage: '模拟请求超时',
  );

  return _decodeResponseMap(
    response,
    fallback: '场景模拟失败',
    requireSuccessFlag: true,
  );
}

Future<Map<String, dynamic>> _trainDeepModel({
  required String storagePath,
  String? modelType = 'lstm',
  int? epochs = 50,
  int? batchSize = 32,
  int? windowSize = 24,
  String? targetColumn,
}) async {
  final response = await _authorizedPost(
    _heavyBaseUrl,
    '/api/ml/deep/train',
    body: jsonEncode(<String, dynamic>{
      'storage_path': storagePath,
      'model_type': modelType,
      'epochs': epochs,
      'batch_size': batchSize,
      'window_size': windowSize,
      if (targetColumn != null) 'target_column': targetColumn,
    }),
    timeout: const Duration(minutes: 10),
    timeoutMessage: '训练请求超时，请稍后刷新查看结果',
  );

  return _decodeResponseMap(
    response,
    fallback: 'Deep Learning training failed',
    requireSuccessFlag: true,
  );
}

Future<Map<String, dynamic>> _askRagQuestion({
  required String question,
  String? collectionName,
}) async {
  final response = await _authorizedPost(
    _heavyBaseUrl,
    '/api/rag/ask',
    body: jsonEncode(<String, dynamic>{
      'query': question,
      if (collectionName != null) 'collection_name': collectionName,
    }),
  );

  return _decodeResponseMap(
    response,
    fallback: 'RAG query failed',
    requireSuccessFlag: true,
  );
}
