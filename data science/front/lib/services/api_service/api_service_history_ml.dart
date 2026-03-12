part of '../api_service.dart';

Future<List<Map<String, dynamic>>> _getUserHistory({int limit = 20}) async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/history',
    queryParameters: <String, Object?>{'limit': limit},
  );
  final data = _decodeResponseMap(
    response,
    fallback: 'Failed to get history',
    requireSuccessFlag: true,
  );
  final payload = data['data'] is Map
      ? Map<String, dynamic>.from(data['data'] as Map)
      : data;
  return List<Map<String, dynamic>>.from(payload['history'] ?? const []);
}

Future<Map<String, dynamic>> _getHistoryDetail(String recordId) async {
  final response = await _authorizedGet(_baseUrl, '/api/history/$recordId');

  if (response.statusCode == 404) {
    throw const ApiServiceException(
      'Record not found',
      statusCode: 404,
      kind: ApiServiceErrorKind.server,
    );
  }

  final data = _decodeResponseMap(
    response,
    fallback: 'Failed to get record',
    requireSuccessFlag: true,
  );
  final payload = data['data'] is Map
      ? Map<String, dynamic>.from(data['data'] as Map)
      : data;

  final record = payload['record'];
  if (record is! Map) {
    throw const ApiServiceException(
      'Failed to get record: record missing',
      kind: ApiServiceErrorKind.badResponse,
    );
  }

  return Map<String, dynamic>.from(record);
}

Future<void> _deleteHistoryRecord(String recordId) async {
  final response = await _authorizedDelete(_baseUrl, '/api/history/$recordId');
  if (!_isSuccessStatus(response.statusCode)) {
    _throwResponseException(response, fallback: 'Failed to delete record');
  }
}

Future<List<Map<String, dynamic>>> _getAuditActivity({
  String? type,
  String? status,
  int limit = 20,
}) async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/history/activity',
    queryParameters: <String, Object?>{
      'limit': limit,
      ...?type == null ? null : <String, Object?>{'type': type},
      ...?status == null ? null : <String, Object?>{'status': status},
    },
  );
  final data = _decodeResponseMap(
    response,
    fallback: 'Failed to get audit activity',
    requireSuccessFlag: true,
  );
  final payload = data['data'] is Map
      ? Map<String, dynamic>.from(data['data'] as Map)
      : data;
  return List<Map<String, dynamic>>.from(payload['activity'] ?? const []);
}

Future<Map<String, dynamic>> _trainModel({
  required String storagePath,
  required String problemType,
  String? targetColumn,
  String? modelName,
  int? nClusters,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/ml/train',
    body: jsonEncode(<String, dynamic>{
      'storage_path': storagePath,
      'problem_type': problemType,
      ...?targetColumn == null
          ? null
          : <String, dynamic>{'target_column': targetColumn},
      ...?modelName == null
          ? null
          : <String, dynamic>{'model_name': modelName},
      ...?nClusters == null ? null : <String, dynamic>{'n_clusters': nClusters},
    }),
    timeout: AppConstants.optimizationTimeout,
  );

  return _decodeResponseMap(
    response,
    fallback: 'Training failed',
    requireSuccessFlag: true,
  );
}

Future<Map<String, dynamic>> _predict({
  required String modelPath,
  List<Map<String, dynamic>>? inputData,
  String? storagePath,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/ml/predict',
    body: jsonEncode(<String, dynamic>{
      'model_path': modelPath,
      ...?inputData == null
          ? null
          : <String, dynamic>{'input_data': inputData},
      ...?storagePath == null
          ? null
          : <String, dynamic>{'storage_path': storagePath},
    }),
    timeout: AppConstants.optimizationTimeout,
  );

  return _decodeResponseMap(
    response,
    fallback: 'Prediction failed',
    requireSuccessFlag: true,
  );
}

Future<List<Map<String, dynamic>>> _listModels() async {
  final response = await _authorizedGet(_baseUrl, '/api/ml/models');
  final data = _decodeResponseMap(
    response,
    fallback: 'Failed to list models',
    requireSuccessFlag: true,
  );
  return List<Map<String, dynamic>>.from(data['models'] ?? const []);
}

Future<Map<String, dynamic>> _getModelInfo(String modelPath) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/ml/model-info',
    body: jsonEncode(<String, dynamic>{'model_path': modelPath}),
  );
  final data = _decodeResponseMap(
    response,
    fallback: 'Failed to get model info',
    requireSuccessFlag: true,
  );
  final info = data['info'];
  if (info is! Map) {
    throw const ApiServiceException(
      'Failed to get model info: info missing',
      kind: ApiServiceErrorKind.badResponse,
    );
  }
  return Map<String, dynamic>.from(info);
}
