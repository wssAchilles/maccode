part of '../api_service.dart';

Future<Map<String, dynamic>> _getRuntimeSnapshot({bool fresh = false}) async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/runtime/snapshot',
    queryParameters: <String, Object?>{if (fresh) 'fresh': true},
    timeout: AppConstants.dashboardTimeout,
    timeoutMessage: '控制台共享快照加载较慢，请稍后重试',
  );
  return _unwrapEnvelopeData(response, fallback: '获取控制台共享快照失败');
}
