/// AI Lab 跳转意图
library;

import 'history_record.dart';
import 'job_record.dart';
import 'workbench_launch_context.dart';

enum AiLabLaunchTarget { deepLearning, rag }

class AiLabLaunchIntent {
  const AiLabLaunchIntent({
    required this.target,
    required this.storagePath,
    this.targetColumn,
    this.collectionName,
    this.resetCollection = false,
    this.sourceLabel,
    this.context,
  });

  final AiLabLaunchTarget target;
  final String storagePath;
  final String? targetColumn;
  final String? collectionName;
  final bool resetCollection;
  final String? sourceLabel;
  final WorkbenchLaunchContext? context;

  factory AiLabLaunchIntent.deepLearning(
    String storagePath, {
    String? targetColumn,
    String? sourceLabel,
    WorkbenchLaunchContext? context,
  }) {
    return AiLabLaunchIntent(
      target: AiLabLaunchTarget.deepLearning,
      storagePath: storagePath,
      targetColumn: targetColumn,
      sourceLabel: sourceLabel,
      context: context,
    );
  }

  factory AiLabLaunchIntent.rag(
    String storagePath, {
    String? collectionName,
    bool resetCollection = false,
    String? sourceLabel,
    WorkbenchLaunchContext? context,
  }) {
    return AiLabLaunchIntent(
      target: AiLabLaunchTarget.rag,
      storagePath: storagePath,
      collectionName: collectionName,
      resetCollection: resetCollection,
      sourceLabel: sourceLabel,
      context: context,
    );
  }

  factory AiLabLaunchIntent.fromTrainingJob(JobRecord job) {
    final storagePath = _firstString([
      job.input['storage_path'],
      job.result['storage_path'],
    ]);
    return AiLabLaunchIntent.deepLearning(
      storagePath ?? '',
      targetColumn: _firstString([
        job.result['target_column'],
        job.input['target_column'],
      ]),
      sourceLabel: '${job.displayTitle} ${job.jobId.substring(0, 8)}',
      context: null,
    );
  }

  factory AiLabLaunchIntent.fromRagJob(JobRecord job) {
    final storagePath = _firstString([
      job.result['storage_path'],
      job.input['storage_path'],
    ]);
    return AiLabLaunchIntent.rag(
      storagePath ?? '',
      collectionName: _firstString([
        job.result['collection'],
        job.input['collection_name'],
      ]),
      resetCollection: _asBool(job.input['reset']) ?? false,
      sourceLabel: '${job.displayTitle} ${job.jobId.substring(0, 8)}',
      context: null,
    );
  }

  factory AiLabLaunchIntent.fromHistoryRecordForTraining(HistoryRecord record) {
    return AiLabLaunchIntent.deepLearning(
      record.storageUrl ?? '',
      targetColumn: _firstNumericColumn(record),
      sourceLabel: record.filename,
      context: null,
    );
  }

  factory AiLabLaunchIntent.fromHistoryRecordForRag(HistoryRecord record) {
    return AiLabLaunchIntent.rag(
      record.storageUrl ?? '',
      sourceLabel: record.filename,
      context: null,
    );
  }

  static String? _firstNumericColumn(HistoryRecord record) {
    final columnTypes = record.basicInfo?['column_types'];
    if (columnTypes is! Map) {
      return null;
    }
    for (final entry in columnTypes.entries) {
      final type = entry.value?.toString().toLowerCase() ?? '';
      if (type.contains('int') ||
          type.contains('float') ||
          type.contains('double') ||
          type.contains('num')) {
        return entry.key.toString();
      }
    }
    return null;
  }

  static String? _firstString(List<Object?> values) {
    for (final value in values) {
      if (value is String && value.isNotEmpty) {
        return value;
      }
    }
    return null;
  }

  static bool? _asBool(Object? value) {
    if (value is bool) {
      return value;
    }
    if (value is num) {
      return value != 0;
    }
    if (value is String) {
      final normalized = value.toLowerCase();
      if (normalized == 'true' || normalized == '1') {
        return true;
      }
      if (normalized == 'false' || normalized == '0') {
        return false;
      }
    }
    return null;
  }
}
