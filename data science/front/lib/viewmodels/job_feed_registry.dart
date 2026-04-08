library;

import 'package:flutter/foundation.dart';

import '../models/workbench_runtime_models.dart';
import '../repositories/job_repository.dart';
import 'job_view_model.dart';

class JobFeedRegistry extends ChangeNotifier {
  JobFeedRegistry({JobRepository? repository}) : _repository = repository;

  final JobRepository? _repository;
  final Map<JobFeedKey, JobViewModel> _feeds = <JobFeedKey, JobViewModel>{};
  final Set<JobFeedKey> _initializedFeeds = <JobFeedKey>{};
  final Set<JobFeedKey> _activeFeeds = <JobFeedKey>{};
  bool _isDisposed = false;

  JobViewModel feedFor(JobFeedKey key) {
    return _feeds.putIfAbsent(key, () {
      final config = _feedConfigFor(key);
      final viewModel = JobViewModel(
        repository: _repository,
        jobType: config.jobType,
        limit: config.limit,
      );
      _notifySafely();
      return viewModel;
    });
  }

  JobViewModel get optimizationFeed => feedFor(JobFeedKey.optimization);
  JobViewModel get analysisFeed => feedFor(JobFeedKey.analysis);
  JobViewModel get mlTrainFeed => feedFor(JobFeedKey.mlTrain);
  JobViewModel get ragIngestFeed => feedFor(JobFeedKey.ragIngest);
  JobViewModel get historyAuditFeed => feedFor(JobFeedKey.historyAudit);

  Future<void> activateForTab(WorkbenchTab tab) async {
    await activateFeeds(_feedsForTab(tab));
  }

  Future<void> activateFeeds(Iterable<JobFeedKey> keys) async {
    final nextActive = keys.toSet();
    for (final entry in _feeds.entries) {
      entry.value.setWorkspaceActive(nextActive.contains(entry.key));
    }

    _activeFeeds
      ..clear()
      ..addAll(nextActive);

    for (final key in nextActive) {
      final feed = feedFor(key);
      feed.setWorkspaceActive(true);
      if (_initializedFeeds.add(key)) {
        await feed.loadJobs();
      }
    }
    _notifySafely();
  }

  void deactivateAll() {
    for (final feed in _feeds.values) {
      feed.setWorkspaceActive(false);
    }
    _activeFeeds.clear();
    _notifySafely();
  }

  Set<JobFeedKey> _feedsForTab(WorkbenchTab tab) {
    return switch (tab) {
      WorkbenchTab.operationsHub => <JobFeedKey>{},
      WorkbenchTab.modeling => <JobFeedKey>{JobFeedKey.optimization},
      WorkbenchTab.dataAnalysis => <JobFeedKey>{JobFeedKey.analysis},
      WorkbenchTab.aiLab => <JobFeedKey>{
        JobFeedKey.mlTrain,
        JobFeedKey.ragIngest,
      },
      WorkbenchTab.historyAudit => <JobFeedKey>{JobFeedKey.historyAudit},
    };
  }

  _JobFeedConfig _feedConfigFor(JobFeedKey key) {
    return switch (key) {
      JobFeedKey.optimization => const _JobFeedConfig(
        jobType: 'optimization',
        limit: 8,
      ),
      JobFeedKey.analysis => const _JobFeedConfig(
        jobType: 'analysis',
        limit: 8,
      ),
      JobFeedKey.mlTrain => const _JobFeedConfig(
        jobType: 'ml_train',
        limit: 8,
      ),
      JobFeedKey.ragIngest => const _JobFeedConfig(
        jobType: 'rag_ingest',
        limit: 8,
      ),
      JobFeedKey.historyAudit => const _JobFeedConfig(limit: 20),
    };
  }

  void _notifySafely() {
    if (!_isDisposed) {
      notifyListeners();
    }
  }

  @override
  void dispose() {
    _isDisposed = true;
    for (final feed in _feeds.values) {
      feed.dispose();
    }
    _feeds.clear();
    super.dispose();
  }
}

class _JobFeedConfig {
  const _JobFeedConfig({this.jobType, required this.limit});

  final String? jobType;
  final int limit;
}
