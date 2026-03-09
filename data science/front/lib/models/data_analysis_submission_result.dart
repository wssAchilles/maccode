/// 数据分析提交结果模型
library;

import 'analysis_result.dart';
import 'data_analysis_error.dart';

class DataAnalysisSubmissionResult {
  const DataAnalysisSubmissionResult._({
    this.analysisResult,
    this.error,
    this.storagePath,
  });

  const DataAnalysisSubmissionResult.success(
    AnalysisResult result, {
    required String storagePath,
  }) : this._(analysisResult: result, storagePath: storagePath);

  const DataAnalysisSubmissionResult.failure(DataAnalysisError error)
    : this._(error: error);

  final AnalysisResult? analysisResult;
  final DataAnalysisError? error;
  final String? storagePath;

  bool get isSuccess => analysisResult != null;
  bool get isFailure => error != null;
}
