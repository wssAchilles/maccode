/// Compute governance repository.
library;

import '../models/compute_rollout_policy.dart';
import '../services/api_service.dart';

abstract class ComputeGovernanceRepository {
  Future<ComputeRolloutPolicy> getPolicy();

  Future<ComputeRolloutPolicy> updateComponentPolicy(
    String componentKey, {
    required String rolloutMode,
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
  Future<ComputeRolloutPolicy> updateComponentPolicy(
    String componentKey, {
    required String rolloutMode,
  }) async {
    final payload = await ApiService.updateComputeRollout(
      components: <String, dynamic>{
        componentKey: <String, dynamic>{'rollout_mode': rolloutMode},
      },
    );
    return ComputeRolloutPolicy.fromJson(payload);
  }
}
