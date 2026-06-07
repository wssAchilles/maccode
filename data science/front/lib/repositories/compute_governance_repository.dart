/// Compute governance repository.
library;

import 'dart:async';

import '../models/compute_rollout_policy.dart';
import '../models/compute_governance_activity_entry.dart';
import '../models/job_record.dart';
import '../services/api_service.dart';

abstract class ComputeGovernanceRepository {
  Future<ComputeRolloutPolicy> getPolicy();
  Future<List<ComputeGovernanceActivityEntry>> getRecentActivity({
    int limit = 8,
  });

  Future<JobRecord> requestComponentPolicyChange(
    String componentKey, {
    required Map<String, dynamic> targetPolicy,
    String? changeReason,
    String requestKind = 'rollout_change',
  });

  Future<JobRecord> requestComponentBenchmark(
    String componentKey, {
    int sampleRows = 5000,
  });
}

class ApiComputeGovernanceRepository implements ComputeGovernanceRepository {
  const ApiComputeGovernanceRepository();

  static ComputeRolloutPolicy? _cachedPolicy;
  static DateTime? _cachedPolicyAt;
  static Future<ComputeRolloutPolicy>? _policyInFlight;
  static final Map<int, List<ComputeGovernanceActivityEntry>> _activityCache =
      <int, List<ComputeGovernanceActivityEntry>>{};
  static final Map<int, DateTime> _activityCacheAt = <int, DateTime>{};
  static final Map<int, Future<List<ComputeGovernanceActivityEntry>>>
  _activityInFlight = <int, Future<List<ComputeGovernanceActivityEntry>>>{};
  static const Duration _cacheTtl = Duration(seconds: 20);

  @override
  Future<ComputeRolloutPolicy> getPolicy() async {
    final now = DateTime.now();
    if (_cachedPolicy != null &&
        _cachedPolicyAt != null &&
        now.difference(_cachedPolicyAt!) < _cacheTtl) {
      return _cachedPolicy!;
    }
    final inflight = _policyInFlight;
    if (inflight != null) {
      return inflight;
    }
    final request = _loadPolicy();
    _policyInFlight = request;
    try {
      return await request;
    } finally {
      if (identical(_policyInFlight, request)) {
        _policyInFlight = null;
      }
    }
  }

  @override
  Future<List<ComputeGovernanceActivityEntry>> getRecentActivity({
    int limit = 8,
  }) async {
    final now = DateTime.now();
    final cached = _activityCache[limit];
    final cachedAt = _activityCacheAt[limit];
    if (cached != null &&
        cachedAt != null &&
        now.difference(cachedAt) < _cacheTtl) {
      return cached;
    }
    final inflight = _activityInFlight[limit];
    if (inflight != null) {
      return inflight;
    }
    final request = _loadRecentActivity(limit);
    _activityInFlight[limit] = request;
    try {
      return await request;
    } finally {
      if (identical(_activityInFlight[limit], request)) {
        _activityInFlight.remove(limit);
      }
    }
  }

  @override
  Future<JobRecord> requestComponentPolicyChange(
    String componentKey, {
    required Map<String, dynamic> targetPolicy,
    String? changeReason,
    String requestKind = 'rollout_change',
  }) async {
    final payload = await ApiService.requestComputeRolloutChange(
      components: <String, dynamic>{componentKey: targetPolicy},
      changeReason: changeReason,
      requestKind: requestKind,
    );
    _clearCache();
    return JobRecord.fromJson(payload);
  }

  Future<JobRecord> updateComponentPolicy(
    String componentKey, {
    required String rolloutMode,
  }) {
    return requestComponentPolicyChange(
      componentKey,
      targetPolicy: <String, dynamic>{'rollout_mode': rolloutMode},
    );
  }

  @override
  Future<JobRecord> requestComponentBenchmark(
    String componentKey, {
    int sampleRows = 5000,
  }) async {
    final payload = await ApiService.requestComputeBenchmark(
      component: componentKey,
      sampleRows: sampleRows,
    );
    _clearCache();
    return JobRecord.fromJson(payload);
  }

  Future<ComputeRolloutPolicy> _loadPolicy() async {
    final payload = await ApiService.getComputeRollout();
    final policy = ComputeRolloutPolicy.fromJson(payload);
    _cachedPolicy = policy;
    _cachedPolicyAt = DateTime.now();
    return policy;
  }

  Future<List<ComputeGovernanceActivityEntry>> _loadRecentActivity(
    int limit,
  ) async {
    final items = await ApiService.getComputeGovernanceActivity(limit: limit);
    final records = items
        .map(ComputeGovernanceActivityEntry.fromJson)
        .toList(growable: false);
    _activityCache[limit] = records;
    _activityCacheAt[limit] = DateTime.now();
    return records;
  }

  static void _clearCache() {
    _cachedPolicy = null;
    _cachedPolicyAt = null;
    _activityCache.clear();
    _activityCacheAt.clear();
  }
}
