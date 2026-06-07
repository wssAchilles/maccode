/// 审计活动 ViewModel
library;

import 'package:flutter/foundation.dart';

import '../models/job_record.dart';
import '../repositories/audit_repository.dart';

class AuditViewModel extends ChangeNotifier {
  AuditViewModel({AuditRepository? repository})
    : _repository = repository ?? GatewayAuditRepository();

  final AuditRepository _repository;

  List<AuditActivity> _activity = const [];
  bool _isLoading = false;
  String? _errorMessage;
  String? _typeFilter;
  String? _statusFilter;
  bool _isDisposed = false;

  List<AuditActivity> get activity => List.unmodifiable(_activity);
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  String? get typeFilter => _typeFilter;
  String? get statusFilter => _statusFilter;

  Future<void> initialize() => loadActivity();

  Future<void> loadActivity({
    String? type,
    String? status,
    int limit = 50,
  }) async {
    _typeFilter = type ?? _typeFilter;
    _statusFilter = status ?? _statusFilter;
    _isLoading = true;
    _errorMessage = null;
    _notifySafely();

    try {
      _activity = await _repository.getActivity(
        type: _typeFilter,
        status: _statusFilter,
        limit: limit,
      );
    } catch (e) {
      _errorMessage = '加载审计活动失败: $e';
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  Future<void> applyFilters({String? type, String? status, int limit = 50}) {
    _typeFilter = type;
    _statusFilter = status;
    return loadActivity(limit: limit);
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
