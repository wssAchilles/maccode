/// 作业中心 ViewModel
library;

import 'dart:async';
import 'dart:convert';

import 'package:flutter/foundation.dart';

import '../models/job_record.dart';
import '../repositories/job_repository.dart';
import '../services/api_service_exception.dart';

class JobViewModel extends ChangeNotifier {
  JobViewModel({
    JobRepository? repository,
    String? jobType,
    String? statusFilter,
    this.limit = 20,
    Future<void> Function(Duration)? delay,
  }) : _jobType = jobType,
       _statusFilter = statusFilter,
       _repository = repository ?? const ApiJobRepository(),
       _delay = delay ?? Future<void>.delayed;

  final JobRepository _repository;
  final Future<void> Function(Duration) _delay;
  final int limit;
  String? _jobType;
  String? _statusFilter;

  List<JobRecord> _jobs = const [];
  bool _isLoading = false;
  bool _isSubmitting = false;
  String? _errorMessage;
  bool _isDisposed = false;
  bool _isPolling = false;
  String? _activeJobId;

  List<JobRecord> get jobs => List.unmodifiable(_jobs);
  bool get isLoading => _isLoading;
  bool get isSubmitting => _isSubmitting;
  String? get errorMessage => _errorMessage;
  String? get activeJobId => _activeJobId;
  String? get jobType => _jobType;
  String? get statusFilter => _statusFilter;
  JobRecord? get activeJob {
    final activeJobId = _activeJobId;
    if (activeJobId == null) {
      return _jobs.cast<JobRecord?>().firstWhere(
        (job) => job?.isRunning == true,
        orElse: () => null,
      );
    }

    return _jobs.cast<JobRecord?>().firstWhere(
      (job) => job?.jobId == activeJobId,
      orElse: () => null,
    );
  }

  Future<void> loadJobs() async {
    _isLoading = true;
    _errorMessage = null;
    _notifySafely();

    try {
      _jobs = await _repository.listJobs(
        type: _jobType,
        status: _statusFilter,
        limit: limit,
      );
      _promoteActiveJob();
      if (!_isPolling && activeJob?.isRunning == true) {
        unawaited(startPolling());
      }
    } catch (e) {
      if (!(_isPolling && _jobs.isNotEmpty && _isTransientApiError(e))) {
        _errorMessage = '加载任务失败: ${_readableErrorMessage(e)}';
      }
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  Future<JobRecord?> submitOptimizationJob({
    required double initialSoc,
    DateTime? targetDate,
    double? batteryCapacity,
    double? batteryPower,
    double? batteryEfficiency,
    double? temperatureAdjust,
  }) async {
    return _submitJob(() {
      return _repository.createOptimizationJob(
        initialSoc: initialSoc,
        targetDate: targetDate,
        batteryCapacity: batteryCapacity,
        batteryPower: batteryPower,
        batteryEfficiency: batteryEfficiency,
        temperatureAdjust: temperatureAdjust,
      );
    });
  }

  Future<JobRecord?> submitMlTrainJob({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    required String targetColumn,
  }) async {
    return _submitJob(() {
      return _repository.createMlTrainJob(
        storagePath: storagePath,
        modelType: modelType,
        epochs: epochs,
        batchSize: batchSize,
        windowSize: windowSize,
        targetColumn: targetColumn,
      );
    });
  }

  Future<JobRecord?> submitRagIngestJob({
    required String storagePath,
    String? collectionName,
    bool reset = false,
  }) async {
    return _submitJob(() {
      return _repository.createRagIngestJob(
        storagePath: storagePath,
        collectionName: collectionName,
        reset: reset,
      );
    });
  }

  Future<JobRecord?> retryJob(String jobId) {
    return _submitJob(
      () => _repository.retryJob(jobId),
      failureLabel: '重试任务失败',
    );
  }

  Future<void> startPolling({
    Duration interval = const Duration(seconds: 4),
  }) async {
    if (_isPolling || _isDisposed) {
      return;
    }

    _isPolling = true;
    while (_isPolling && !_isDisposed) {
      await loadJobs();
      final active = activeJob;
      if (active == null || active.isTerminal) {
        if (_activeJobId != null && active?.isTerminal == true) {
          _activeJobId = active!.jobId;
          _notifySafely();
        }
        _isPolling = false;
        break;
      }
      await _delay(interval);
    }
  }

  void stopPolling() {
    _isPolling = false;
  }

  Future<void> applyFilters({String? jobType, String? statusFilter}) {
    _jobType = jobType;
    _statusFilter = statusFilter;
    return loadJobs();
  }

  Future<JobRecord?> _submitJob(
    Future<JobRecord> Function() action, {
    String failureLabel = '创建任务失败',
  }) async {
    if (_isSubmitting) {
      return null;
    }

    _isSubmitting = true;
    _errorMessage = null;
    _notifySafely();

    try {
      final job = await action();
      _activeJobId = job.jobId;
      _jobs = [job, ..._jobs.where((item) => item.jobId != job.jobId)].toList();
      _notifySafely();
      unawaited(startPolling());
      return job;
    } catch (e) {
      final detail = _readableErrorMessage(e);
      _errorMessage = detail.startsWith(failureLabel)
          ? detail
          : '$failureLabel: $detail';
      _notifySafely();
      return null;
    } finally {
      _isSubmitting = false;
      _notifySafely();
    }
  }

  void _promoteActiveJob() {
    final activeJobId = _activeJobId;
    if (activeJobId != null) {
      final match = _jobs.cast<JobRecord?>().firstWhere(
        (job) => job?.jobId == activeJobId,
        orElse: () => null,
      );
      if (match != null) {
        _activeJobId = match.jobId;
        return;
      }
    }

    final running = _jobs.cast<JobRecord?>().firstWhere(
      (job) => job?.isRunning == true,
      orElse: () => null,
    );
    _activeJobId = running?.jobId;
  }

  void _notifySafely() {
    if (!_isDisposed) {
      notifyListeners();
    }
  }

  String _readableErrorMessage(Object error) {
    if (error is ApiServiceException) {
      if (error.statusCode == 503) {
        final detail =
            _extractApiErrorMessage(error.body) ??
            (error.body?.contains('JOB_BACKEND_UNAVAILABLE') == true
                ? '当前部署环境未启用 Firestore Native 模式，任务中心暂不可用'
                : null);
        if (detail != null && detail.isNotEmpty) {
          return detail;
        }
        return '当前部署环境未启用 Firestore Native 模式，任务中心暂不可用';
      }
      final detail = _extractApiErrorMessage(error.body);
      if (detail != null && detail.isNotEmpty) {
        return detail;
      }
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

  String? _extractApiErrorMessage(String? body) {
    if (body == null || body.trim().isEmpty) {
      return null;
    }

    try {
      final decoded = jsonDecode(body);
      if (decoded is! Map) {
        return null;
      }
      final direct = decoded['message'] ?? decoded['detail'];
      if (direct is String && direct.trim().isNotEmpty) {
        return direct.trim();
      }
      final error = decoded['error'];
      if (error is String && error.trim().isNotEmpty) {
        return error.trim();
      }
      if (error is Map) {
        final nested = error['message'];
        if (nested is String && nested.trim().isNotEmpty) {
          return nested.trim();
        }
      }
    } catch (_) {
      return null;
    }

    return null;
  }

  @override
  void dispose() {
    _isDisposed = true;
    _isPolling = false;
    super.dispose();
  }
}
