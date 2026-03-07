/// 深度学习页面训练参数状态
library;

enum DeepLearningModelType { lstm, gru }

class DeepLearningConfigState {
  const DeepLearningConfigState({
    required this.modelType,
    required this.epochs,
    required this.windowSize,
    required this.batchSize,
  });

  const DeepLearningConfigState.initial()
    : modelType = DeepLearningModelType.lstm,
      epochs = 50,
      windowSize = 24,
      batchSize = 32;

  final DeepLearningModelType modelType;
  final int epochs;
  final int windowSize;
  final int batchSize;

  String get modelTypeValue => modelType.name;

  DeepLearningConfigState copyWith({
    DeepLearningModelType? modelType,
    int? epochs,
    int? windowSize,
    int? batchSize,
  }) {
    return DeepLearningConfigState(
      modelType: modelType ?? this.modelType,
      epochs: epochs ?? this.epochs,
      windowSize: windowSize ?? this.windowSize,
      batchSize: batchSize ?? this.batchSize,
    );
  }
}
