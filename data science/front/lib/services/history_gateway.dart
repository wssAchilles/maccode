/// 历史记录网关接口
library;

import 'api_client.dart';

abstract class HistoryGateway {
  Future<List<Map<String, dynamic>>> getUserHistory({int limit = 50});

  Future<List<Map<String, dynamic>>> getAuditActivity({
    String? type,
    String? status,
    int limit = 50,
  });

  Future<void> deleteHistoryRecord(String recordId);
}

class ApiHistoryGateway implements HistoryGateway {
  ApiHistoryGateway({ApiClient? apiClient})
    : _apiClient = apiClient ?? const DefaultApiClient();

  final ApiClient _apiClient;

  @override
  Future<List<Map<String, dynamic>>> getUserHistory({int limit = 50}) {
    return _apiClient.getUserHistory(limit: limit);
  }

  @override
  Future<List<Map<String, dynamic>>> getAuditActivity({
    String? type,
    String? status,
    int limit = 50,
  }) {
    return _apiClient.getAuditActivity(type: type, status: status, limit: limit);
  }

  @override
  Future<void> deleteHistoryRecord(String recordId) {
    return _apiClient.deleteHistoryRecord(recordId);
  }
}
