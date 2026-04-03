part of '../api_service.dart';

Future<List<Map<String, dynamic>>> _listControlTasks({
  String? kind,
  bool? enabled,
  String? owner,
  int limit = 20,
}) async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/control-tasks',
    queryParameters: <String, Object?>{
      'limit': limit,
      ...?kind == null ? null : <String, Object?>{'kind': kind},
      ...?enabled == null ? null : <String, Object?>{'enabled': enabled},
      ...?owner == null ? null : <String, Object?>{'owner': owner},
    },
    timeout: AppConstants.jobPollingTimeout,
    timeoutMessage: '规划任务列表加载较慢，请稍后刷新查看',
  );
  final data = _unwrapEnvelopeData(response, fallback: '获取规划任务列表失败');
  return List<Map<String, dynamic>>.from(data['control_tasks'] ?? const []);
}

Future<Map<String, dynamic>> _getControlTask(String controlTaskId) async {
  final response = await _authorizedGet(
    _baseUrl,
    '/api/control-tasks/$controlTaskId',
    timeout: AppConstants.jobPollingTimeout,
    timeoutMessage: '规划任务详情加载较慢，请稍后刷新查看',
  );
  return _unwrapEnvelopeData(response, fallback: '获取规划任务详情失败');
}

Future<Map<String, dynamic>> _runControlTask(
  String controlTaskId, {
  Map<String, dynamic>? input,
  String trigger = 'manual',
}) async {
  final response = await _authorizedPost(
    _baseUrl,
    '/api/control-tasks/$controlTaskId/run',
    body: jsonEncode(<String, dynamic>{
      'trigger': trigger,
      ...?input == null ? null : <String, dynamic>{'input': input},
    }),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '触发规划任务失败');
}

Future<Map<String, dynamic>> _setControlTaskEnabled(
  String controlTaskId, {
  required bool enabled,
}) async {
  final response = await _authorizedPatch(
    _baseUrl,
    '/api/control-tasks/$controlTaskId',
    body: jsonEncode(<String, dynamic>{'enabled': enabled}),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '更新规划任务状态失败');
}

Future<Map<String, dynamic>> _setControlTaskApprovalPolicy(
  String controlTaskId, {
  required Map<String, dynamic> approvalPolicy,
}) async {
  final response = await _authorizedPatch(
    _baseUrl,
    '/api/control-tasks/$controlTaskId',
    body: jsonEncode(<String, dynamic>{'approval_policy': approvalPolicy}),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '更新规划任务审批策略失败');
}

Future<Map<String, dynamic>> _updateControlTaskDefinition(
  String controlTaskId, {
  String? schedule,
  String? owner,
  required List<String> dependencies,
  required Map<String, dynamic> approvalPolicy,
  required Map<String, dynamic> defaultInput,
}) async {
  final response = await _authorizedPatch(
    _baseUrl,
    '/api/control-tasks/$controlTaskId',
    body: jsonEncode(<String, dynamic>{
      'schedule': schedule,
      'owner': owner,
      'dependencies': dependencies,
      'approval_policy': approvalPolicy,
      'default_input': defaultInput,
    }),
    timeout: AppConstants.optimizationTimeout,
  );
  return _unwrapEnvelopeData(response, fallback: '更新规划任务定义失败');
}
