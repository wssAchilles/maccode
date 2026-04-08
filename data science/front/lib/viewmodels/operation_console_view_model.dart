/// Real-time operation console view model.
library;

import 'dart:async';

import 'package:flutter/widgets.dart';

import '../models/job_record.dart';
import '../models/job_stream_frame.dart';
import '../repositories/operation_repository.dart';
import '../services/api_service_exception.dart';
import '../utils/job_stream_merge.dart';

class OperationConsoleViewModel extends ChangeNotifier
    with WidgetsBindingObserver {
  OperationConsoleViewModel({
    OperationRepository? repository,
    Future<void> Function(Duration)? delay,
  }) : _repository = repository ?? const ApiOperationRepository(),
       _delay = delay ?? Future<void>.delayed {
    WidgetsBinding.instance.addObserver(this);
  }

  final OperationRepository _repository;
  final Future<void> Function(Duration) _delay;

  JobRecord? _selectedOperation;
  String? _selectedOperationId;
  bool _isLoading = false;
  bool _isStreaming = false;
  bool _isActing = false;
  String? _errorMessage;
  bool _isDisposed = false;
  bool _isForeground = true;
  bool _isWorkspaceActive = true;
  int _streamToken = 0;
  StreamSubscription<JobStreamFrame>? _streamSubscription;

  JobRecord? get selectedOperation => _selectedOperation;
  String? get selectedOperationId => _selectedOperationId;
  bool get isLoading => _isLoading;
  bool get isStreaming => _isStreaming;
  bool get isActing => _isActing;
  String? get errorMessage => _errorMessage;

  Future<void> selectOperation(String operationId, {JobRecord? seed}) async {
    _selectedOperationId = operationId;
    if (seed != null) {
      _selectedOperation = seed;
    }
    _isLoading = true;
    _errorMessage = null;
    _notifySafely();

    try {
      _selectedOperation = await _repository.getOperation(operationId);
    } catch (error) {
      _errorMessage = '加载运行详情失败: ${_readableError(error)}';
    } finally {
      _isLoading = false;
      _notifySafely();
    }

    _restartStreaming();
  }

  Future<void> refreshSelected() async {
    final operationId = _selectedOperationId;
    if (operationId == null) {
      return;
    }
    await selectOperation(operationId, seed: _selectedOperation);
  }

  void clearSelection() {
    _streamToken += 1;
    _cancelActiveStream();
    _selectedOperation = null;
    _selectedOperationId = null;
    _isStreaming = false;
    _errorMessage = null;
    _notifySafely();
  }

  Future<JobRecord?> cancelSelected() {
    final current = _selectedOperation;
    if (current == null) {
      return Future<JobRecord?>.value(null);
    }
    return _runOperationAction(
      () => _repository.cancelOperation(current.operationId ?? current.jobId),
      failureLabel: '取消运行失败',
      restartStreaming: false,
    );
  }

  Future<JobRecord?> retrySelected() {
    final current = _selectedOperation;
    if (current == null) {
      return Future<JobRecord?>.value(null);
    }
    return _runOperationAction(
      () => _repository.retryOperation(current.operationId ?? current.jobId),
      failureLabel: '重试运行失败',
      restartStreaming: true,
    );
  }

  Future<JobRecord?> resolveSelectedApproval({
    required bool approved,
    String? message,
  }) {
    final current = _selectedOperation;
    if (current == null) {
      return Future<JobRecord?>.value(null);
    }
    return _runOperationAction(
      () => _repository.approveOperation(
        current.operationId ?? current.jobId,
        approved: approved,
        message: message,
      ),
      failureLabel: approved ? '批准运行失败' : '驳回运行失败',
      restartStreaming: approved,
    );
  }

  Future<JobRecord?> _runOperationAction(
    Future<JobRecord> Function() action, {
    required String failureLabel,
    required bool restartStreaming,
  }) async {
    if (_isActing) {
      return null;
    }

    _isActing = true;
    _errorMessage = null;
    _notifySafely();
    try {
      final updated = await action();
      _selectedOperationId = updated.operationId ?? updated.jobId;
      _selectedOperation = updated;
      _notifySafely();
      if (restartStreaming) {
        _restartStreaming();
      }
      return updated;
    } catch (error) {
      _errorMessage = '$failureLabel: ${_readableError(error)}';
      _notifySafely();
      return null;
    } finally {
      _isActing = false;
      _notifySafely();
    }
  }

  void _restartStreaming() {
    final current = _selectedOperation;
    final operationId = _selectedOperationId;
    _streamToken += 1;
    _cancelActiveStream();
    if (!_isRuntimeActive ||
        current == null ||
        operationId == null ||
        current.isTerminal) {
      _isStreaming = false;
      _notifySafely();
      return;
    }
    final token = _streamToken;
    unawaited(_streamLoop(operationId, token));
  }

  Future<void> _streamLoop(String operationId, int token) async {
    while (!_isDisposed &&
        _isRuntimeActive &&
        _selectedOperationId == operationId &&
        token == _streamToken) {
      final current = _selectedOperation;
      if (current == null || current.isTerminal) {
        _isStreaming = false;
        _notifySafely();
        return;
      }

      _isStreaming = true;
      _notifySafely();
      try {
        final shouldContinue = await _consumeOperationStream(operationId, token);
        if (!shouldContinue) {
          return;
        }
      } catch (error) {
        if (!_isDisposed &&
            token == _streamToken &&
            _selectedOperationId == operationId &&
            !_isTransientApiError(error)) {
          _errorMessage = '实时流连接失败: ${_readableError(error)}';
          _notifySafely();
        }
      } finally {
        if (!_isDisposed && token == _streamToken) {
          _isStreaming = false;
          _notifySafely();
        }
      }

      if (_isDisposed ||
          !_isRuntimeActive ||
          token != _streamToken ||
          _selectedOperationId != operationId) {
        return;
      }

      try {
        _selectedOperation = await _repository.getOperation(operationId);
        _notifySafely();
      } catch (_) {
        // Keep the last streamed snapshot and retry the live stream loop.
      }

      if (_selectedOperation == null || _selectedOperation!.isTerminal) {
        return;
      }
      await _delay(const Duration(milliseconds: 400));
    }
  }

  Future<bool> _consumeOperationStream(String operationId, int token) async {
    final completer = Completer<bool>();
    StreamSubscription<JobStreamFrame>? subscription;

    void finish(bool shouldContinue) {
      if (!completer.isCompleted) {
        completer.complete(shouldContinue);
      }
    }

    subscription = _repository.streamOperation(operationId).listen(
      (frame) {
        if (_isDisposed ||
            !_isRuntimeActive ||
            token != _streamToken ||
            _selectedOperationId != operationId) {
          finish(false);
          unawaited(subscription?.cancel() ?? Future<void>.value());
          return;
        }
        _applyStreamFrame(frame);
        final refreshed = _selectedOperation;
        if (refreshed == null || refreshed.isTerminal) {
          finish(false);
          unawaited(subscription?.cancel() ?? Future<void>.value());
        }
      },
      onError: (Object error, StackTrace _) {
        if (!_isDisposed &&
            token == _streamToken &&
            _selectedOperationId == operationId &&
            !_isTransientApiError(error)) {
          _errorMessage = '实时流连接失败: ${_readableError(error)}';
          _notifySafely();
        }
        finish(
          _isRuntimeActive &&
              token == _streamToken &&
              _selectedOperationId == operationId,
        );
      },
      onDone: () {
        finish(
          _isRuntimeActive &&
              token == _streamToken &&
              _selectedOperationId == operationId,
        );
      },
      cancelOnError: false,
    );

    _streamSubscription = subscription;
    try {
      return await completer.future;
    } finally {
      if (identical(_streamSubscription, subscription)) {
        _streamSubscription = null;
      }
      await subscription.cancel();
    }
  }

  @override
  void didChangeAppLifecycleState(AppLifecycleState state) {
    final wasForeground = _isForeground;
    _isForeground = switch (state) {
      AppLifecycleState.resumed => true,
      AppLifecycleState.inactive => false,
      AppLifecycleState.hidden => false,
      AppLifecycleState.paused => false,
      AppLifecycleState.detached => false,
    };
    if (_isDisposed || wasForeground == _isForeground) {
      return;
    }
    if (!_isRuntimeActive) {
      _streamToken += 1;
      _cancelActiveStream();
      return;
    }
    _restartStreaming();
  }

  void setWorkspaceActive(bool isActive) {
    if (_isDisposed || _isWorkspaceActive == isActive) {
      return;
    }
    _isWorkspaceActive = isActive;
    if (!_isRuntimeActive) {
      _streamToken += 1;
      _cancelActiveStream();
      return;
    }
    _restartStreaming();
  }

  void _applyStreamFrame(JobStreamFrame frame) {
    final current = _selectedOperation;
    if (current == null) {
      return;
    }
    _selectedOperation = mergeJobStreamFrame(current, frame);
    _notifySafely();
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

  bool get _isRuntimeActive => _isForeground && _isWorkspaceActive;

  void _cancelActiveStream() {
    final subscription = _streamSubscription;
    _streamSubscription = null;
    _isStreaming = false;
    _notifySafely();
    if (subscription != null) {
      unawaited(subscription.cancel());
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    _streamToken += 1;
    _cancelActiveStream();
    WidgetsBinding.instance.removeObserver(this);
    super.dispose();
  }
}
