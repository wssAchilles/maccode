/// 数据分析网关接口
/// 为 ViewModel 提供可替换的数据访问层，便于单元测试
library;

import '../models/analysis_result.dart';
import 'api_client.dart';

abstract class DataAnalysisGateway {
  Future<Map<String, dynamic>> getUploadUrl({
    required String fileName,
    required String contentType,
  });

  Future<void> uploadFileToGcs({
    required String uploadUrl,
    required List<int> fileData,
    required String contentType,
  });

  Future<AnalysisResult> analyzeCsv({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  });

  Future<Map<String, dynamic>> createAnalysisJob({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  });
}

class ApiDataAnalysisGateway implements DataAnalysisGateway {
  ApiDataAnalysisGateway({ApiClient? apiClient})
    : _apiClient = apiClient ?? const DefaultApiClient();

  final ApiClient _apiClient;

  @override
  Future<Map<String, dynamic>> getUploadUrl({
    required String fileName,
    required String contentType,
  }) {
    return _apiClient.getUploadUrl(
      fileName: fileName,
      contentType: contentType,
    );
  }

  @override
  Future<void> uploadFileToGcs({
    required String uploadUrl,
    required List<int> fileData,
    required String contentType,
  }) {
    return _apiClient.uploadFileToGcs(
      uploadUrl: uploadUrl,
      fileData: fileData,
      contentType: contentType,
    );
  }

  @override
  Future<AnalysisResult> analyzeCsv({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  }) {
    return _apiClient.analyzeCsv(
      storagePath: storagePath,
      filename: filename,
      saveToStorage: saveToStorage,
    );
  }

  @override
  Future<Map<String, dynamic>> createAnalysisJob({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  }) {
    return _apiClient.createAnalysisJob(
      storagePath: storagePath,
      filename: filename,
      saveToStorage: saveToStorage,
    );
  }
}
