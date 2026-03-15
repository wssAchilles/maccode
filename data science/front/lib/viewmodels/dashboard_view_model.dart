/// 驾驶舱 ViewModel
library;

import 'package:flutter/foundation.dart';

import '../models/dashboard_summary.dart';
import '../repositories/dashboard_repository.dart';
import '../services/api_service_exception.dart';

class DashboardViewModel extends ChangeNotifier {
  DashboardViewModel({DashboardRepository? repository})
    : _repository = repository ?? const ApiDashboardRepository();

  final DashboardRepository _repository;

  DashboardSummary? _summary;
  bool _isLoading = false;
  String? _errorMessage;
  bool _isDisposed = false;
  bool _isInitialized = false;

  DashboardSummary? get summary => _summary;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> initialize() async {
    if (_isInitialized) {
      return;
    }
    _isInitialized = true;
    await loadSummary();
  }

  Future<void> loadSummary() async {
    _isLoading = true;
    _errorMessage = null;
    _notifySafely();

    try {
      _summary = await _repository.getSummary();
    } catch (e) {
      if (!(_summary != null && _isTransientApiError(e))) {
        _errorMessage = '加载驾驶舱摘要失败: ${_readableErrorMessage(e)}';
      }
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  String _readableErrorMessage(Object error) {
    if (error is ApiServiceException) {
      return error.message;
    }
    return error.toString();
  }

  bool _isTransientApiError(Object error) {
    if (error is! ApiServiceException) {
      return false;
    }
    return error.kind == ApiServiceErrorKind.timeout ||
        error.kind == ApiServiceErrorKind.server;
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
