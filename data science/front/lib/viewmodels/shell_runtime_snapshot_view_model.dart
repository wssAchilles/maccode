library;

import 'package:flutter/foundation.dart';

import '../models/shell_runtime_snapshot.dart';
import '../repositories/shell_runtime_snapshot_repository.dart';
import '../services/api_service_exception.dart';

class ShellRuntimeSnapshotViewModel extends ChangeNotifier {
  ShellRuntimeSnapshotViewModel({ShellRuntimeSnapshotRepository? repository})
    : _repository = repository ?? const ApiShellRuntimeSnapshotRepository();

  final ShellRuntimeSnapshotRepository _repository;

  ShellRuntimeSnapshot? _snapshot;
  bool _isLoading = false;
  String? _errorMessage;
  bool _isDisposed = false;
  bool _isInitialized = false;

  ShellRuntimeSnapshot? get snapshot => _snapshot;
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;

  Future<void> initialize() async {
    if (_isInitialized) {
      return;
    }
    _isInitialized = true;
    await loadSnapshot();
  }

  Future<ShellRuntimeSnapshot?> loadSnapshot({bool force = false}) async {
    _isLoading = true;
    _errorMessage = null;
    _notifySafely();
    try {
      _snapshot = await _repository.getSnapshot(force: force);
      return _snapshot;
    } catch (error) {
      if (_snapshot == null || !_isTransientApiError(error)) {
        _errorMessage = '加载共享运行时快照失败: ${_readableError(error)}';
      }
      return _snapshot;
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  String _readableError(Object error) {
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
