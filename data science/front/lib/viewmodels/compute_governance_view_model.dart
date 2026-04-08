/// Compute governance view model.
library;

import 'package:flutter/foundation.dart';

import '../models/compute_governance_activity_entry.dart';
import '../models/compute_rollout_policy.dart';
import '../models/job_record.dart';
import '../repositories/compute_governance_repository.dart';
import '../services/api_service_exception.dart';

class ComputeGovernanceViewModel extends ChangeNotifier {
  ComputeGovernanceViewModel({ComputeGovernanceRepository? repository})
    : _repository = repository ?? const ApiComputeGovernanceRepository();

  final ComputeGovernanceRepository _repository;

  ComputeRolloutPolicy _policy = const ComputeRolloutPolicy.empty();
  List<ComputeGovernanceActivityEntry> _recentActivity =
      const <ComputeGovernanceActivityEntry>[];
  bool _isLoading = false;
  String? _errorMessage;
  bool _isDisposed = false;
  bool _isInitialized = false;
  final Set<String> _updatingComponents = <String>{};

  ComputeRolloutPolicy get policy => _policy;
  List<ComputeGovernanceActivityEntry> get recentActivity => _recentActivity;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool isUpdatingComponent(String componentKey) =>
      _updatingComponents.contains(componentKey);

  Future<void> initialize() async {
    if (_isInitialized) {
      return;
    }
    _isInitialized = true;
    await loadPolicy();
  }

  Future<void> loadPolicy() async {
    _isLoading = true;
    _errorMessage = null;
    _notifySafely();

    try {
      _policy = await _repository.getPolicy();
      _recentActivity = await _repository.getRecentActivity();
    } catch (e) {
      _errorMessage = '加载计算层治理策略失败: ${_readableErrorMessage(e)}';
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  void hydrateSnapshot({
    required ComputeRolloutPolicy policy,
    required List<ComputeGovernanceActivityEntry> activity,
  }) {
    _policy = policy;
    _recentActivity = List<ComputeGovernanceActivityEntry>.unmodifiable(
      activity,
    );
    _isInitialized = true;
    _isLoading = false;
    _errorMessage = null;
    _notifySafely();
  }

  Future<JobRecord?> requestRolloutModeChange(
    String componentKey, {
    required Map<String, dynamic> targetPolicy,
    String? changeReason,
    String requestKind = 'rollout_change',
  }) async {
    if (_updatingComponents.contains(componentKey)) {
      return null;
    }

    _updatingComponents.add(componentKey);
    _errorMessage = null;
    _notifySafely();

    try {
      final operation = await _repository.requestComponentPolicyChange(
        componentKey,
        targetPolicy: targetPolicy,
        changeReason: changeReason,
        requestKind: requestKind,
      );
      return operation;
    } catch (e) {
      _errorMessage = '提交计算层治理变更失败: ${_readableErrorMessage(e)}';
      _notifySafely();
      return null;
    } finally {
      _updatingComponents.remove(componentKey);
      _notifySafely();
    }
  }

  Future<JobRecord?> updateRolloutMode(
    String componentKey, {
    required String rolloutMode,
  }) {
    return requestRolloutModeChange(
      componentKey,
      targetPolicy: <String, dynamic>{'rollout_mode': rolloutMode},
    );
  }

  Future<JobRecord?> requestBenchmark(
    String componentKey, {
    int sampleRows = 5000,
  }) async {
    if (_updatingComponents.contains(componentKey)) {
      return null;
    }

    _updatingComponents.add(componentKey);
    _errorMessage = null;
    _notifySafely();

    try {
      return await _repository.requestComponentBenchmark(
        componentKey,
        sampleRows: sampleRows,
      );
    } catch (e) {
      _errorMessage = '提交 benchmark 失败: ${_readableErrorMessage(e)}';
      _notifySafely();
      return null;
    } finally {
      _updatingComponents.remove(componentKey);
      _notifySafely();
    }
  }

  String _readableErrorMessage(Object error) {
    if (error is ApiServiceException) {
      return error.message;
    }
    return error.toString();
  }

  void _notifySafely() {
    if (!_isDisposed) {
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    super.dispose();
  }
}
