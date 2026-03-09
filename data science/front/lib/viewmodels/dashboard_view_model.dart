/// 驾驶舱 ViewModel
library;

import 'package:flutter/foundation.dart';

import '../models/dashboard_summary.dart';
import '../repositories/dashboard_repository.dart';

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
      _errorMessage = '加载驾驶舱摘要失败: $e';
    } finally {
      _isLoading = false;
      _notifySafely();
    }
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
