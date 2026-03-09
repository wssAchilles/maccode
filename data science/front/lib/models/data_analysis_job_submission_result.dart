/// 数据分析后台任务提交结果
library;

import 'data_analysis_error.dart';
import 'job_record.dart';

class DataAnalysisJobSubmissionResult {
  const DataAnalysisJobSubmissionResult._({
    this.job,
    this.error,
    this.storagePath,
  });

  const DataAnalysisJobSubmissionResult.success(
    JobRecord job, {
    required String storagePath,
  }) : this._(job: job, storagePath: storagePath);

  const DataAnalysisJobSubmissionResult.failure(DataAnalysisError error)
    : this._(error: error);

  final JobRecord? job;
  final DataAnalysisError? error;
  final String? storagePath;

  bool get isSuccess => job != null;
}
