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

Future<Map<String, dynamic>> _updateComputeRollout({
  required Map<String, dynamic> components,
}) async {
  final response = await _authorizedPatch(
    _baseUrl,
    '/api/compute/rollout',
    body: jsonEncode(<String, dynamic>{'components': components}),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '更新计算治理策略失败');
}
