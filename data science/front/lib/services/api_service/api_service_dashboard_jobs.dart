part of '../api_service.dart';

Map<String, dynamic> _unwrapEnvelopeData(
  http.Response response, {
  required String fallback,
}) {
  final payload = _decodeResponseMap(
    response,
    fallback: fallback,
    requireSuccessFlag: true,
  );
  final data = payload['data'];
  if (data is Map<String, dynamic>) {
    return data;
  }
  if (data is Map) {
    return Map<String, dynamic>.from(data);
  }
  throw ApiServiceException(
    '$fallback: data missing',
    kind: ApiServiceErrorKind.badResponse,
    body: response.body,
  );
}

Future<Map<String, dynamic>> _getDashboardSummary() async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/dashboard/summary',
    timeout: AppConstants.dashboardTimeout,
    timeoutMessage: '驾驶舱数据加载较慢，请稍后重试',
  );
  return _unwrapEnvelopeData(response, fallback: '获取驾驶舱摘要失败');
}

Future<Map<String, dynamic>> _getDashboardAssets() async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/dashboard/assets',
    timeout: AppConstants.dashboardTimeout,
    timeoutMessage: '资产摘要加载较慢，请稍后重试',
  );
  return _unwrapEnvelopeData(response, fallback: '获取资产摘要失败');
}

Future<List<Map<String, dynamic>>> _listJobs({
  String? type,
  String? status,
  int limit = 20,
}) async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/jobs',
    queryParameters: <String, Object?>{
      'limit': limit,
      ...?type == null ? null : <String, Object?>{'type': type},
      ...?status == null ? null : <String, Object?>{'status': status},
    },
    timeout: AppConstants.jobPollingTimeout,
    timeoutMessage: '任务队列响应较慢，请稍后刷新查看',
  );
  final data = _unwrapEnvelopeData(response, fallback: '获取任务列表失败');
  return List<Map<String, dynamic>>.from(data['jobs'] ?? const []);
}

Future<Map<String, dynamic>> _getJob(String jobId) async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/jobs/$jobId',
    timeout: AppConstants.jobPollingTimeout,
    timeoutMessage: '任务详情加载较慢，请稍后刷新查看',
  );
  return _unwrapEnvelopeData(response, fallback: '获取任务详情失败');
}

Future<Map<String, dynamic>> _retryJob(String jobId) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/jobs/$jobId/retry',
    body: jsonEncode(const <String, dynamic>{}),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '重试任务失败');
}

Future<List<Map<String, dynamic>>> _listOperations({
  String? type,
  String? status,
  int limit = 20,
}) async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/operations',
    queryParameters: <String, Object?>{
      'limit': limit,
      ...?type == null ? null : <String, Object?>{'type': type},
      ...?status == null ? null : <String, Object?>{'status': status},
    },
    timeout: AppConstants.jobPollingTimeout,
    timeoutMessage: '运行控制台响应较慢，请稍后刷新查看',
  );
  final data = _unwrapEnvelopeData(response, fallback: '获取任务运行列表失败');
  return List<Map<String, dynamic>>.from(data['operations'] ?? const []);
}

Future<Map<String, dynamic>> _createOperation({
  required String type,
  required Map<String, dynamic> input,
  String? controlTaskId,
  String trigger = 'manual',
  Map<String, dynamic>? approvalPolicy,
  Map<String, dynamic>? metadata,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/operations',
    body: jsonEncode(<String, dynamic>{
      'type': type,
      'input': input,
      'trigger': trigger,
      ...?controlTaskId == null
          ? null
          : <String, dynamic>{'control_task_id': controlTaskId},
      ...?approvalPolicy == null
          ? null
          : <String, dynamic>{'approval_policy': approvalPolicy},
      ...?metadata == null ? null : <String, dynamic>{'metadata': metadata},
    }),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '创建任务运行失败');
}

Future<Map<String, dynamic>> _getOperation(String operationId) async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/operations/$operationId',
    timeout: AppConstants.jobPollingTimeout,
    timeoutMessage: '任务运行详情加载较慢，请稍后刷新查看',
  );
  return _unwrapEnvelopeData(response, fallback: '获取任务运行详情失败');
}

Future<List<Map<String, dynamic>>> _getOperationEvents(
  String operationId, {
  int limit = 50,
}) async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/operations/$operationId/events',
    queryParameters: <String, Object?>{'limit': limit},
    timeout: AppConstants.jobPollingTimeout,
    timeoutMessage: '任务事件流加载较慢，请稍后刷新查看',
  );
  final data = _unwrapEnvelopeData(response, fallback: '获取任务事件失败');
  return List<Map<String, dynamic>>.from(data['events'] ?? const []);
}

Future<Map<String, dynamic>> _cancelOperation(String operationId) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/operations/$operationId/cancel',
    body: jsonEncode(const <String, dynamic>{}),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '取消任务失败');
}

Future<Map<String, dynamic>> _retryOperation(String operationId) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/operations/$operationId/retry',
    body: jsonEncode(const <String, dynamic>{}),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '重试任务运行失败');
}

Future<Map<String, dynamic>> _approveOperation(
  String operationId, {
  required bool approved,
  String? message,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/operations/$operationId/approve',
    body: jsonEncode(<String, dynamic>{
      'approved': approved,
      ...?message == null ? null : <String, dynamic>{'message': message},
    }),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '审批任务失败');
}

Future<Map<String, dynamic>> _createOptimizationJob({
  required double initialSoc,
  DateTime? targetDate,
  double? batteryCapacity,
  double? batteryPower,
  double? batteryEfficiency,
  double? temperatureAdjust,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/jobs/optimization',
    body: jsonEncode(<String, dynamic>{
      'initial_soc': initialSoc,
      ...?targetDate == null
          ? null
          : <String, dynamic>{'target_date': _formatDate(targetDate)},
      ...?batteryCapacity == null
          ? null
          : <String, dynamic>{'battery_capacity': batteryCapacity},
      ...?batteryPower == null
          ? null
          : <String, dynamic>{'battery_power': batteryPower},
      ...?batteryEfficiency == null
          ? null
          : <String, dynamic>{'battery_efficiency': batteryEfficiency},
      ...?temperatureAdjust == null
          ? null
          : <String, dynamic>{'temperature_adjust': temperatureAdjust},
    }),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '创建优化任务失败');
}

Future<Map<String, dynamic>> _createAnalysisJob({
  required String storagePath,
  String? filename,
  bool saveToStorage = true,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/jobs/analysis',
    body: jsonEncode(<String, dynamic>{
      'storage_path': storagePath,
      'save_to_storage': saveToStorage,
      ...?filename == null ? null : <String, dynamic>{'filename': filename},
    }),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '创建分析任务失败');
}

Future<Map<String, dynamic>> _createMlTrainJob({
  required String storagePath,
  required String modelType,
  required int epochs,
  required int batchSize,
  required int windowSize,
  required String targetColumn,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/jobs/ml-train',
    body: jsonEncode(<String, dynamic>{
      'storage_path': storagePath,
      'model_type': modelType,
      'epochs': epochs,
      'batch_size': batchSize,
      'window_size': windowSize,
      'target_column': targetColumn,
    }),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '创建训练任务失败');
}

Future<Map<String, dynamic>> _createRagIngestJob({
  required String storagePath,
  String? collectionName,
  bool reset = false,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/jobs/rag-ingest',
    body: jsonEncode(<String, dynamic>{
      'storage_path': storagePath,
      'reset': reset,
      ...?collectionName == null || collectionName.isEmpty
          ? null
          : <String, dynamic>{'collection_name': collectionName},
    }),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '创建知识库构建任务失败');
}
