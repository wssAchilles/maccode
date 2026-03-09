/// 驾驶舱仓储
library;

import '../models/dashboard_summary.dart';
import '../services/api_service.dart';

abstract class DashboardRepository {
  Future<DashboardSummary> getSummary();
}

class ApiDashboardRepository implements DashboardRepository {
  const ApiDashboardRepository();

  @override
  Future<DashboardSummary> getSummary() async {
    final payload = await ApiService.getDashboardSummary();
    return DashboardSummary.fromJson(payload);
  }
}
