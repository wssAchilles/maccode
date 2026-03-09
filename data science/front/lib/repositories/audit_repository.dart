/// 审计活动仓储
library;

import '../models/job_record.dart';
import '../services/history_gateway.dart';

abstract class AuditRepository {
  Future<List<AuditActivity>> getActivity({
    String? type,
    String? status,
    int limit = 50,
  });
}

class GatewayAuditRepository implements AuditRepository {
  GatewayAuditRepository({HistoryGateway? historyGateway})
    : _historyGateway = historyGateway ?? ApiHistoryGateway();

  final HistoryGateway _historyGateway;

  @override
  Future<List<AuditActivity>> getActivity({
    String? type,
    String? status,
    int limit = 50,
  }) async {
    final raw = await _historyGateway.getAuditActivity(
      type: type,
      status: status,
      limit: limit,
    );
    return raw.map(AuditActivity.fromJson).toList(growable: false);
  }
}
