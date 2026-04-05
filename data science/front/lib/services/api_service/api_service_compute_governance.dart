part of '../api_service.dart';

Future<Map<String, dynamic>> _getComputeRollout() async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/compute/rollout',
    timeout: AppConstants.dashboardTimeout,
    timeoutMessage: '计算治理策略加载较慢，请稍后重试',
  );
  return _unwrapEnvelopeData(response, fallback: '获取计算治理策略失败');
}

Future<List<Map<String, dynamic>>> _getComputeGovernanceActivity({
  int limit = 8,
}) async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/compute/activity?limit=$limit',
    timeout: AppConstants.dashboardTimeout,
    timeoutMessage: '计算治理活动加载较慢，请稍后重试',
  );
  final payload = _unwrapEnvelopeData(response, fallback: '获取计算治理活动失败');
  final entries = payload['entries'];
  if (entries is! List) {
    return const <Map<String, dynamic>>[];
  }
  return entries
      .whereType<Map>()
      .map((item) => Map<String, dynamic>.from(item))
      .toList(growable: false);
}

Future<Map<String, dynamic>> _requestComputeRolloutChange({
  required Map<String, dynamic> components,
  String? changeReason,
  String requestKind = 'rollout_change',
}) async {
  final response = await _authorizedPatch(
    _baseUrl,
    '/api/compute/rollout',
    body: jsonEncode(<String, dynamic>{
      'components': components,
      'change_reason': changeReason,
      'request_kind': requestKind,
    }),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '提交计算治理变更失败');
}

Future<Map<String, dynamic>> _requestComputeBenchmark({
  required String component,
  int sampleRows = 5000,
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/compute/benchmark',
    body: jsonEncode(<String, dynamic>{
      'component': component,
      'sample_rows': sampleRows,
    }),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '提交 benchmark 失败');
}
