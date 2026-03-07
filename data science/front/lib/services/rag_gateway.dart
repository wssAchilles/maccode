/// RAG 网关接口
library;

import 'api_client.dart';

abstract class RagGateway {
  Future<Map<String, dynamic>> askQuestion({required String question});
}

class ApiRagGateway implements RagGateway {
  ApiRagGateway({ApiClient? apiClient})
    : _apiClient = apiClient ?? const DefaultApiClient();

  final ApiClient _apiClient;

  @override
  Future<Map<String, dynamic>> askQuestion({required String question}) {
    return _apiClient.askRagQuestion(question: question);
  }
}
