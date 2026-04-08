/// 规划任务控制台 ViewModel
library;

import 'package:flutter/foundation.dart';

import '../models/control_task_record.dart';
import '../models/job_record.dart';
import '../repositories/control_task_repository.dart';
import '../services/api_service_exception.dart';

class ControlTaskViewModel extends ChangeNotifier {
  ControlTaskViewModel({ControlTaskRepository? repository})
    : _repository = repository ?? const ApiControlTaskRepository();

  final ControlTaskRepository _repository;

  List<ControlTaskRecord> _tasks = const <ControlTaskRecord>[];
  bool _isLoading = false;
  String? _errorMessage;
  bool _isDisposed = false;
  bool _isInitialized = false;
  final Set<String> _runningTaskIds = <String>{};
  final Set<String> _updatingTaskIds = <String>{};

  List<ControlTaskRecord> get tasks => List.unmodifiable(_tasks);
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool isRunningTask(String controlTaskId) =>
      _runningTaskIds.contains(controlTaskId);
  bool isUpdatingTask(String controlTaskId) =>
      _updatingTaskIds.contains(controlTaskId);

  Future<void> initialize() async {
    if (_isInitialized) {
      return;
    }
    _isInitialized = true;
    await loadControlTasks();
  }

  Future<void> loadControlTasks({
    String? kind,
    bool? enabled,
    String? owner,
    int limit = 6,
  }) async {
    _isLoading = true;
    _errorMessage = null;
    _notifySafely();

    try {
      _tasks = await _repository.listControlTasks(
        kind: kind,
        enabled: enabled,
        owner: owner,
        limit: limit,
      );
    } catch (e) {
      if (!(_tasks.isNotEmpty && _isTransientApiError(e))) {
        _errorMessage = '加载规划任务失败: ${_readableErrorMessage(e)}';
      }
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  void hydrateTasks(List<ControlTaskRecord> tasks) {
    _tasks = List<ControlTaskRecord>.unmodifiable(tasks);
    _isInitialized = true;
    _isLoading = false;
    _errorMessage = null;
    _notifySafely();
  }

  Future<JobRecord?> runControlTask(
    ControlTaskRecord task, {
    Map<String, dynamic>? inputOverrides,
    String trigger = 'manual',
  }) async {
    if (_runningTaskIds.contains(task.id)) {
      return null;
    }

    _runningTaskIds.add(task.id);
    _errorMessage = null;
    _notifySafely();

    try {
      return await _repository.runControlTask(
        task.id,
        input: inputOverrides,
        trigger: trigger,
      );
    } catch (e) {
      _errorMessage = '触发规划任务失败: ${_readableErrorMessage(e)}';
      _notifySafely();
      return null;
    } finally {
      _runningTaskIds.remove(task.id);
      _notifySafely();
    }
  }

  Future<ControlTaskRecord?> setControlTaskEnabled(
    ControlTaskRecord task, {
    required bool enabled,
  }) async {
    if (_updatingTaskIds.contains(task.id)) {
      return null;
    }

    _updatingTaskIds.add(task.id);
    _errorMessage = null;
    _notifySafely();

    try {
      final updated = await _repository.setControlTaskEnabled(
        task.id,
        enabled: enabled,
      );
      _tasks = _tasks
          .map((item) => item.id == updated.id ? updated : item)
          .toList(growable: false);
      _notifySafely();
      return updated;
    } catch (e) {
      _errorMessage = '更新规划任务状态失败: ${_readableErrorMessage(e)}';
      _notifySafely();
      return null;
    } finally {
      _updatingTaskIds.remove(task.id);
      _notifySafely();
    }
  }

  Future<ControlTaskRecord?> setControlTaskApprovalPolicy(
    ControlTaskRecord task, {
    required Map<String, dynamic> approvalPolicy,
  }) async {
    if (_updatingTaskIds.contains(task.id)) {
      return null;
    }

    _updatingTaskIds.add(task.id);
    _errorMessage = null;
    _notifySafely();

    try {
      final updated = await _repository.setControlTaskApprovalPolicy(
        task.id,
        approvalPolicy: approvalPolicy,
      );
      _tasks = _tasks
          .map((item) => item.id == updated.id ? updated : item)
          .toList(growable: false);
      _notifySafely();
      return updated;
    } catch (e) {
      _errorMessage = '更新规划任务审批策略失败: ${_readableErrorMessage(e)}';
      _notifySafely();
      return null;
    } finally {
      _updatingTaskIds.remove(task.id);
      _notifySafely();
    }
  }

  Future<ControlTaskRecord?> updateControlTaskDefinition(
    ControlTaskRecord task, {
    String? schedule,
    String? owner,
    required List<String> dependencies,
    required Map<String, dynamic> approvalPolicy,
    required Map<String, dynamic> defaultInput,
  }) async {
    if (_updatingTaskIds.contains(task.id)) {
      return null;
    }

    _updatingTaskIds.add(task.id);
    _errorMessage = null;
    _notifySafely();

    try {
      final updated = await _repository.updateControlTaskDefinition(
        task.id,
        schedule: schedule,
        owner: owner,
        dependencies: dependencies,
        approvalPolicy: approvalPolicy,
        defaultInput: defaultInput,
      );
      _tasks = _tasks
          .map((item) => item.id == updated.id ? updated : item)
          .toList(growable: false);
      _notifySafely();
      return updated;
    } catch (e) {
      _errorMessage = '更新规划任务定义失败: ${_readableErrorMessage(e)}';
      _notifySafely();
      return null;
    } finally {
      _updatingTaskIds.remove(task.id);
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
