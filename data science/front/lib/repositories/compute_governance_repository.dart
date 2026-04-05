/// Compute governance repository.
library;

import '../models/compute_rollout_policy.dart';
import '../models/compute_governance_activity_entry.dart';
import '../models/job_record.dart';
import '../services/api_service.dart';

abstract class ComputeGovernanceRepository {
  Future<ComputeRolloutPolicy> getPolicy();
  Future<List<ComputeGovernanceActivityEntry>> getRecentActivity({int limit = 8});

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

  @override
  Future<ComputeRolloutPolicy> getPolicy() async {
    final payload = await ApiService.getComputeRollout();
    return ComputeRolloutPolicy.fromJson(payload);
  }

  @override
  Future<List<ComputeGovernanceActivityEntry>> getRecentActivity({
    int limit = 8,
  }) async {
    final items = await ApiService.getComputeGovernanceActivity(limit: limit);
    return items
        .map(ComputeGovernanceActivityEntry.fromJson)
        .toList(growable: false);
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
    return JobRecord.fromJson(payload);
  }
}
