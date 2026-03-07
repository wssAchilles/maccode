/// 能源优化页面 ViewModel
library;

import 'package:flutter/foundation.dart';

import '../models/optimization_result.dart';
import '../services/optimization_gateway.dart';

class ModelingViewModel extends ChangeNotifier {
  ModelingViewModel({OptimizationGateway? gateway})
    : _gateway = gateway ?? ApiOptimizationGateway();

  final OptimizationGateway _gateway;

  bool _isLoading = false;
  OptimizationResponse? _result;
  OptimizationResponse? _previousResult;
  String? _errorMessage;
  bool _isDisposed = false;

  bool get isLoading => _isLoading;
  OptimizationResponse? get result => _result;
  OptimizationResponse? get previousResult => _previousResult;
  String? get errorMessage => _errorMessage;

  Future<OptimizationResponse?> runOptimization({
    required double initialSoc,
    DateTime? targetDate,
    double? batteryCapacity,
    double? batteryPower,
    double? temperatureAdjust,
    bool saveForComparison = true,
  }) async {
    if (_isLoading) {
      return null;
    }

    _isLoading = true;
    _errorMessage = null;
    if (saveForComparison && _result != null) {
      _previousResult = _result;
    }
    _result = null;
    _notifySafely();

    try {
      final result = await _gateway.runOptimization(
        initialSoc: initialSoc,
        targetDate: targetDate,
        batteryCapacity: batteryCapacity,
        batteryPower: batteryPower,
        temperatureAdjust: temperatureAdjust,
      );

      _result = result;

      if (!result.isSuccess) {
        _errorMessage = result.message ?? result.error ?? '优化失败';
      }

      return result;
    } catch (e) {
      _errorMessage = e.toString();
      return null;
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  void clearError() {
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
