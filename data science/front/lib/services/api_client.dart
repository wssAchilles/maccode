/// API 客户端契约
/// 让各业务网关依赖可注入接口，而不是直接耦合静态 ApiService。
library;

import '../models/analysis_result.dart';
import '../models/optimization_result.dart';
import 'api_service.dart';

abstract interface class ApiClient {
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

  Future<List<Map<String, dynamic>>> getUserHistory({int limit = 20});

  Future<List<Map<String, dynamic>>> getAuditActivity({
    String? type,
    String? status,
    int limit = 20,
  });

  Future<void> deleteHistoryRecord(String recordId);

  Future<OptimizationResponse> runOptimization({
    double initialSoc = 0.5,
    DateTime? targetDate,
    double? temperatureAdjust,
    double? batteryCapacity,
    double? batteryPower,
  });

  Future<Map<String, dynamic>> trainDeepModel({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    String? targetColumn,
  });

  Future<Map<String, dynamic>> askRagQuestion({
    required String question,
    String? collectionName,
  });
}

class DefaultApiClient implements ApiClient {
  const DefaultApiClient();

  @override
  Future<Map<String, dynamic>> getUploadUrl({
    required String fileName,
    required String contentType,
  }) {
    return ApiService.getUploadUrl(
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
    return ApiService.uploadFileToGcs(
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
    return ApiService.analyzeCsv(
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
    return ApiService.createAnalysisJob(
      storagePath: storagePath,
      filename: filename,
      saveToStorage: saveToStorage,
    );
  }

  @override
  Future<List<Map<String, dynamic>>> getUserHistory({int limit = 20}) {
    return ApiService.getUserHistory(limit: limit);
  }

  @override
  Future<List<Map<String, dynamic>>> getAuditActivity({
    String? type,
    String? status,
    int limit = 20,
  }) {
    return ApiService.getAuditActivity(
      type: type,
      status: status,
      limit: limit,
    );
  }

  @override
  Future<void> deleteHistoryRecord(String recordId) {
    return ApiService.deleteHistoryRecord(recordId);
  }

  @override
  Future<OptimizationResponse> runOptimization({
    double initialSoc = 0.5,
    DateTime? targetDate,
    double? temperatureAdjust,
    double? batteryCapacity,
    double? batteryPower,
  }) {
    return ApiService.runOptimization(
      initialSoc: initialSoc,
      targetDate: targetDate,
      temperatureAdjust: temperatureAdjust,
      batteryCapacity: batteryCapacity,
      batteryPower: batteryPower,
    );
  }

  @override
  Future<Map<String, dynamic>> trainDeepModel({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    String? targetColumn,
  }) {
    return ApiService.trainDeepModel(
      storagePath: storagePath,
      modelType: modelType,
      epochs: epochs,
      batchSize: batchSize,
      windowSize: windowSize,
      targetColumn: targetColumn,
    );
  }

  @override
  Future<Map<String, dynamic>> askRagQuestion({
    required String question,
    String? collectionName,
  }) {
    return ApiService.askRagQuestion(
      question: question,
      collectionName: collectionName,
    );
  }
}
