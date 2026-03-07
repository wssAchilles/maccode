/// 数据分析流程错误模型
library;

enum DataAnalysisErrorType {
  auth,
  validation,
  fileSelection,
  upload,
  analysis,
  unknown,
}

class DataAnalysisError {
  const DataAnalysisError({required this.type, required this.message});

  final DataAnalysisErrorType type;
  final String message;
}
