/// Approval queue view model for operations hub.
library;

import 'package:flutter/foundation.dart';

import '../models/job_record.dart';
import '../repositories/job_repository.dart';
import '../services/api_service_exception.dart';

class ApprovalQueueViewModel extends ChangeNotifier {
  ApprovalQueueViewModel({JobRepository? repository})
    : _repository = repository ?? const ApiJobRepository();

  final JobRepository _repository;

  List<JobRecord> _jobs = const <JobRecord>[];
  bool _isLoading = false;
  String? _errorMessage;
  final Set<String> _updatingIds = <String>{};
  bool _isDisposed = false;
  bool _isInitialized = false;

  List<JobRecord> get jobs => List.unmodifiable(_jobs);
  bool get isLoading => _isLoading;
  String? get errorMessage => _errorMessage;
  bool isUpdating(String jobId) => _updatingIds.contains(jobId);

  Future<void> initialize() async {
    if (_isInitialized) {
      return;
    }
    _isInitialized = true;
    await loadQueue();
  }

  Future<void> loadQueue() async {
    _isLoading = true;
    _errorMessage = null;
    _notifySafely();
    try {
      _jobs = await _repository.listJobs(
        status: 'awaiting_approval',
        limit: 20,
        scope: 'control_plane',
      );
    } catch (e) {
      _errorMessage = '加载审批队列失败: ${_readableError(e)}';
    } finally {
      _isLoading = false;
      _notifySafely();
    }
  }

  Future<JobRecord?> resolve(
    JobRecord job, {
    required bool approved,
    String? message,
  }) async {
    if (_updatingIds.contains(job.jobId)) {
      return null;
    }
    _updatingIds.add(job.jobId);
    _errorMessage = null;
    _notifySafely();
    try {
      final updated = await _repository.approveJob(
        job.jobId,
        approved: approved,
        message: message,
        operationId: job.operationId,
      );
      _jobs = _jobs
          .where((item) => item.jobId != job.jobId)
          .toList(growable: false);
      _notifySafely();
      return updated;
    } catch (e) {
      _errorMessage = '${approved ? '批准' : '驳回'}任务失败: ${_readableError(e)}';
      _notifySafely();
      return null;
    } finally {
      _updatingIds.remove(job.jobId);
      _notifySafely();
    }
  }

  String _readableError(Object error) {
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
