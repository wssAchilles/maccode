/// 数据漂移检测 ViewModel
library;

import 'package:flutter/foundation.dart';

import '../models/data_drift_report.dart';
import '../repositories/data_drift_repository.dart';

class DataDriftViewModel extends ChangeNotifier {
  DataDriftViewModel({DataDriftRepository? repository})
    : _repository = repository ?? GatewayDataDriftRepository();

  final DataDriftRepository _repository;

  DataDriftReport? _report;
  bool _isLoading = false;
  String? _errorMessage;
  bool _isDisposed = false;

  DataDriftReport? get report => _report;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<DataDriftReport?> detectDrift({
    required String referencePath,
    required String currentPath,
    required List<String> features,
  }) async {
    if (_isLoading) {
      return null;
    }

    _isLoading = true;
    _errorMessage = null;
    _notifySafely();

    try {
      final report = await _repository.detectDrift(
        referencePath: referencePath,
        currentPath: currentPath,
        features: features,
      );
      _report = report;
      return report;
    } catch (e) {
      _errorMessage = '漂移检测失败: $e';
      return null;
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  void clearReport() {
    _report = null;
    _errorMessage = null;
    _notifySafely();
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
