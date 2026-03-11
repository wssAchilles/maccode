part of '../api_service.dart';

Future<Map<String, dynamic>> _verifyToken() async {
  final response = await _authorizedPost(_baseUrl, '/api/auth/verify');
  return _decodeResponseMap(response, fallback: 'Token verification failed');
}

Future<Map<String, dynamic>> _getUserProfile() async {
  final response = await _authorizedGet(_baseUrl, '/api/auth/profile');
  return _decodeResponseMap(response, fallback: 'Failed to get profile');
}

Future<Map<String, dynamic>> _getUploadUrl({
  required String fileName,
  required String contentType,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/data/upload-url',
    body: jsonEncode(<String, dynamic>{
      'fileName': fileName,
      'contentType': contentType,
    }),
  );
  return _decodeResponseMap(response, fallback: 'Failed to get upload URL');
}

Future<void> _uploadFileToGcs({
  required String uploadUrl,
  required List<int> fileData,
  required String contentType,
}) async {
  final response = await _requestWithTimeout(
    _httpClient.put(
      Uri.parse(uploadUrl),
      headers: <String, String>{'Content-Type': contentType},
      body: fileData,
    ),
    timeout: AppConstants.optimizationTimeout,
  );

  if (!_isSuccessStatus(response.statusCode)) {
    _throwResponseException(response, fallback: 'Failed to upload to GCS');
  }
}

Future<AnalysisResult> _analyzeCsv({
  required String storagePath,
  String? filename,
  bool saveToStorage = true,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/analysis/analyze-csv',
    body: jsonEncode(<String, dynamic>{
      'storage_path': storagePath,
      'filename': filename,
      'save_to_storage': saveToStorage,
    }),
    timeout: const Duration(minutes: 3),
    timeoutMessage: '分析请求超时，请稍后重试或尝试较小的文件',
  );

  final data = _decodeResponseMap(
    response,
    fallback: 'Analysis failed',
    requireSuccessFlag: true,
  );

  final payload = data['data'] is Map
      ? Map<String, dynamic>.from(data['data'])
      : data;
  final analysisData = payload['analysis_result'];
  if (analysisData is! Map) {
    throw const ApiServiceException(
      'Analysis failed: 缺少 analysis_result',
      kind: ApiServiceErrorKind.badResponse,
    );
  }

  try {
    return AnalysisResult.fromJson(Map<String, dynamic>.from(analysisData));
  } on FormatException catch (e) {
    throw ApiServiceException(
      'Analysis failed: ${e.message}',
      kind: ApiServiceErrorKind.badResponse,
    );
  }
}

Future<Map<String, dynamic>> _detectDataDrift({
  required String referencePath,
  required String currentPath,
  required List<String> features,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/analysis/drift/detect',
    body: jsonEncode(<String, dynamic>{
      'reference_path': referencePath,
      'current_path': currentPath,
      'features': features,
    }),
    timeout: const Duration(minutes: 2),
    timeoutMessage: '漂移检测超时，请稍后重试',
  );

  final data = _decodeResponseMap(
    response,
    fallback: 'Drift detection failed',
    requireSuccessFlag: true,
  );
  final payload = data['data'] is Map
      ? Map<String, dynamic>.from(data['data'] as Map)
      : data;

  final rawResults = payload['drift_results'];
  if (rawResults is! Map) {
    throw const ApiServiceException(
      'Drift detection failed: 缺少 drift_results',
      kind: ApiServiceErrorKind.badResponse,
    );
  }

  return <String, dynamic>{
    'drift_results': Map<String, dynamic>.from(rawResults),
    'report': payload['report']?.toString() ?? '',
  };
}

Future<List<String>> _listUserFiles() async {
  final response = await _authorizedGet(_baseUrl, '/api/data/list');
  final data = _decodeResponseMap(response, fallback: 'Failed to list files');
  return List<String>.from(data['files'] ?? const <String>[]);
}

Future<String> _getDownloadUrl(String filePath) async {
  final encodedPath = Uri.encodeComponent(filePath);
  final response = await _authorizedGet(
    _baseUrl,
    '/api/data/download/$encodedPath',
  );
  final data = _decodeResponseMap(
    response,
    fallback: 'Failed to get download URL',
  );
  final downloadUrl = data['downloadUrl'];
  if (downloadUrl is! String || downloadUrl.isEmpty) {
    throw const ApiServiceException(
      'Failed to get download URL: downloadUrl missing',
      kind: ApiServiceErrorKind.badResponse,
    );
  }
  return downloadUrl;
}

Future<bool> _checkHealth() async {
  try {
    final response = await _publicGet(
      _baseUrl,
      '/api/health',
      timeout: const Duration(seconds: 5),
    );
    return response.statusCode == 200;
  } catch (_) {
    return false;
  }
}
