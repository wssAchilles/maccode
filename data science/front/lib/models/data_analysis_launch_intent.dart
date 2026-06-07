/// 数据分析工作台跳转意图
library;

import 'analysis_result.dart';
import 'history_record.dart';
import 'job_record.dart';
import 'workbench_launch_context.dart';

class DataAnalysisLaunchIntent {
  const DataAnalysisLaunchIntent({
    required this.analysisResult,
    this.storagePath,
    this.filename,
    this.savedAsAsset = false,
    this.sourceLabel,
    this.context,
  });

  final AnalysisResult? analysisResult;
  final String? storagePath;
  final String? filename;
  final bool savedAsAsset;
  final String? sourceLabel;
  final WorkbenchLaunchContext? context;

  bool get canHydrate => analysisResult != null;

  factory DataAnalysisLaunchIntent.workspace({
    String? sourceLabel,
    WorkbenchLaunchContext? context,
  }) {
    return DataAnalysisLaunchIntent(
      analysisResult: null,
      sourceLabel: sourceLabel,
      context: context,
    );
  }

  factory DataAnalysisLaunchIntent.fromHistoryRecord(
    HistoryRecord record, {
    String? sourceLabel,
    WorkbenchLaunchContext? context,
  }) {
    return DataAnalysisLaunchIntent(
      analysisResult: _parseAnalysisResult(record.summary),
      storagePath: record.storageUrl,
      filename: record.filename,
      savedAsAsset: (record.storageUrl?.isNotEmpty ?? false),
      sourceLabel: sourceLabel ?? record.filename,
      context: context,
    );
  }

  factory DataAnalysisLaunchIntent.fromJob(
    JobRecord job, {
    String? sourceLabel,
    WorkbenchLaunchContext? context,
  }) {
    final resultMap = _asMap(job.result['analysis_result']);
    final storagePath = _firstString([
      job.result['storage_path'],
      job.input['storage_path'],
    ]);
    final filename = _firstString([
      job.result['filename'],
      job.input['filename'],
    ]);
    final retained = job.result['storage_retained'];

    return DataAnalysisLaunchIntent(
      analysisResult: _parseAnalysisResult(resultMap),
      storagePath: storagePath,
      filename: filename,
      savedAsAsset: retained is bool
          ? retained
          : (storagePath != null && storagePath.isNotEmpty),
      sourceLabel:
          sourceLabel ?? '${job.displayTitle} ${job.jobId.substring(0, 8)}',
      context: context,
    );
  }

  static AnalysisResult? _parseAnalysisResult(Map<String, dynamic>? payload) {
    if (payload == null) {
      return null;
    }
    try {
      return AnalysisResult.fromJson(payload);
    } catch (_) {
      return null;
    }
  }

  static Map<String, dynamic>? _asMap(Object? value) {
    if (value is Map<String, dynamic>) {
      return value;
    }
    if (value is Map) {
      return Map<String, dynamic>.from(value);
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
}
