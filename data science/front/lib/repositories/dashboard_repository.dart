/// 驾驶舱仓储
library;

import 'dart:async';

import '../models/dashboard_summary.dart';
import '../services/api_service.dart';

abstract class DashboardRepository {
  Future<DashboardSummary> getSummary();
}

class ApiDashboardRepository implements DashboardRepository {
  const ApiDashboardRepository();

  static DashboardSummary? _cachedSummary;
  static DateTime? _cachedAt;
  static Future<DashboardSummary>? _inFlight;
  static const Duration _cacheTtl = Duration(seconds: 20);

  @override
  Future<DashboardSummary> getSummary() async {
    final now = DateTime.now();
    if (_cachedSummary != null &&
        _cachedAt != null &&
        now.difference(_cachedAt!) < _cacheTtl) {
      return _cachedSummary!;
    }
    final inflight = _inFlight;
    if (inflight != null) {
      return inflight;
    }
    final request = _loadSummary();
    _inFlight = request;
    try {
      return await request;
    } finally {
      if (identical(_inFlight, request)) {
        _inFlight = null;
      }
    }
  }

  Future<DashboardSummary> _loadSummary() async {
    final payload = await ApiService.getDashboardSummary();
    final summary = DashboardSummary.fromJson(payload);
    _cachedSummary = summary;
    _cachedAt = DateTime.now();
    return summary;
  }
}
