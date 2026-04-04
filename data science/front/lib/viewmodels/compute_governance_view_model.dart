/// Compute governance view model.
library;

import 'package:flutter/foundation.dart';

import '../models/compute_rollout_policy.dart';
import '../repositories/compute_governance_repository.dart';
import '../services/api_service_exception.dart';

class ComputeGovernanceViewModel extends ChangeNotifier {
  ComputeGovernanceViewModel({ComputeGovernanceRepository? repository})
    : _repository = repository ?? const ApiComputeGovernanceRepository();

  final ComputeGovernanceRepository _repository;

  ComputeRolloutPolicy _policy = const ComputeRolloutPolicy.empty();
  bool _isLoading = false;
  String? _errorMessage;
  bool _isDisposed = false;
  bool _isInitialized = false;
  final Set<String> _updatingComponents = <String>{};

  ComputeRolloutPolicy get policy => _policy;
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
    } catch (e) {
      _errorMessage = '加载计算层治理策略失败: ${_readableErrorMessage(e)}';
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  Future<ComputeRolloutPolicy?> updateRolloutMode(
    String componentKey, {
    required String rolloutMode,
  }) async {
    if (_updatingComponents.contains(componentKey)) {
      return null;
    }

    _updatingComponents.add(componentKey);
    _errorMessage = null;
    _notifySafely();

    try {
      final updated = await _repository.updateComponentPolicy(
        componentKey,
        rolloutMode: rolloutMode,
      );
      _policy = updated;
      _notifySafely();
      return updated;
    } catch (e) {
      _errorMessage = '更新计算层治理策略失败: ${_readableErrorMessage(e)}';
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
