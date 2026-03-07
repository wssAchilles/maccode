/// 深度学习训练网关接口
library;

import 'api_client.dart';

abstract class DeepLearningGateway {
  Future<Map<String, dynamic>> trainModel({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    String? targetColumn,
  });
}

class ApiDeepLearningGateway implements DeepLearningGateway {
  ApiDeepLearningGateway({ApiClient? apiClient})
    : _apiClient = apiClient ?? const DefaultApiClient();

  final ApiClient _apiClient;

  @override
  Future<Map<String, dynamic>> trainModel({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    String? targetColumn,
  }) {
    return _apiClient.trainDeepModel(
      storagePath: storagePath,
      modelType: modelType,
      epochs: epochs,
      batchSize: batchSize,
      windowSize: windowSize,
      targetColumn: targetColumn,
    );
  }
}
