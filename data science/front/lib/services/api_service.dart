/// API 服务层
/// 封装所有后端 API 调用，并统一错误与 JSON 处理。
library;

import 'dart:convert';

import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/foundation.dart' show visibleForTesting;
import 'package:http/http.dart' as http;

import '../config/constants.dart';
import '../models/analysis_result.dart';
import '../models/optimization_result.dart';
import 'api_service_exception.dart';

part 'api_service/api_service_auth_data.dart';
part 'api_service/api_service_core.dart';
part 'api_service/api_service_dashboard_jobs.dart';
part 'api_service/api_service_history_ml.dart';
part 'api_service/api_service_optimization.dart';

class ApiService {
  @visibleForTesting
  static void setHttpClientForTesting(http.Client client) {
    _httpClient = client;
  }

  @visibleForTesting
  static void setTokenProviderForTesting(Future<String?> Function()? provider) {
    _tokenProviderOverride = provider;
  }

  @visibleForTesting
  static void resetTestingOverrides() {
    _httpClient = http.Client();
    _tokenProviderOverride = null;
  }

  static Future<Map<String, dynamic>> verifyToken() => _verifyToken();

  static Future<Map<String, dynamic>> getUserProfile() => _getUserProfile();

  static Future<Map<String, dynamic>> getUploadUrl({
    required String fileName,
    required String contentType,
  }) => _getUploadUrl(fileName: fileName, contentType: contentType);

  static Future<void> uploadFileToGcs({
    required String uploadUrl,
    required List<int> fileData,
    required String contentType,
  }) => _uploadFileToGcs(
    uploadUrl: uploadUrl,
    fileData: fileData,
    contentType: contentType,
  );

  static Future<AnalysisResult> analyzeCsv({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  }) => _analyzeCsv(
    storagePath: storagePath,
    filename: filename,
    saveToStorage: saveToStorage,
  );

  static Future<List<String>> listUserFiles() => _listUserFiles();

  static Future<String> getDownloadUrl(String filePath) =>
      _getDownloadUrl(filePath);

  static Future<bool> checkHealth() => _checkHealth();

  static Future<Map<String, dynamic>> getDashboardSummary() =>
      _getDashboardSummary();

  static Future<List<Map<String, dynamic>>> listJobs({
    String? type,
    String? status,
    int limit = 20,
  }) => _listJobs(type: type, status: status, limit: limit);

  static Future<Map<String, dynamic>> getJob(String jobId) => _getJob(jobId);

  static Future<Map<String, dynamic>> retryJob(String jobId) =>
      _retryJob(jobId);

  static Future<Map<String, dynamic>> createOptimizationJob({
    required double initialSoc,
    DateTime? targetDate,
    double? batteryCapacity,
    double? batteryPower,
    double? batteryEfficiency,
    double? temperatureAdjust,
  }) => _createOptimizationJob(
    initialSoc: initialSoc,
    targetDate: targetDate,
    batteryCapacity: batteryCapacity,
    batteryPower: batteryPower,
    batteryEfficiency: batteryEfficiency,
    temperatureAdjust: temperatureAdjust,
  );

  static Future<Map<String, dynamic>> createAnalysisJob({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  }) => _createAnalysisJob(
    storagePath: storagePath,
    filename: filename,
    saveToStorage: saveToStorage,
  );

  static Future<Map<String, dynamic>> createMlTrainJob({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    required String targetColumn,
  }) => _createMlTrainJob(
    storagePath: storagePath,
    modelType: modelType,
    epochs: epochs,
    batchSize: batchSize,
    windowSize: windowSize,
    targetColumn: targetColumn,
  );

  static Future<Map<String, dynamic>> createRagIngestJob({
    required String storagePath,
    String? collectionName,
    bool reset = false,
  }) => _createRagIngestJob(
    storagePath: storagePath,
    collectionName: collectionName,
    reset: reset,
  );

  static Future<List<Map<String, dynamic>>> getUserHistory({int limit = 20}) =>
      _getUserHistory(limit: limit);

  static Future<List<Map<String, dynamic>>> getAuditActivity({
    String? type,
    String? status,
    int limit = 20,
  }) => _getAuditActivity(type: type, status: status, limit: limit);

  static Future<Map<String, dynamic>> getHistoryDetail(String recordId) =>
      _getHistoryDetail(recordId);

  static Future<void> deleteHistoryRecord(String recordId) =>
      _deleteHistoryRecord(recordId);

  static Future<Map<String, dynamic>> trainModel({
    required String storagePath,
    required String problemType,
    String? targetColumn,
    String? modelName,
    int? nClusters,
  }) => _trainModel(
    storagePath: storagePath,
    problemType: problemType,
    targetColumn: targetColumn,
    modelName: modelName,
    nClusters: nClusters,
  );

  static Future<Map<String, dynamic>> predict({
    required String modelPath,
    List<Map<String, dynamic>>? inputData,
    String? storagePath,
  }) => _predict(
    modelPath: modelPath,
    inputData: inputData,
    storagePath: storagePath,
  );

  static Future<List<Map<String, dynamic>>> listModels() => _listModels();

  static Future<Map<String, dynamic>> getModelInfo(String modelPath) =>
      _getModelInfo(modelPath);

  static Future<OptimizationResponse> runOptimization({
    double initialSoc = AppConstants.defaultInitialSoc,
    DateTime? targetDate,
    List<double>? temperatureForecast,
    double? temperatureAdjust,
    double? batteryCapacity,
    double? batteryPower,
    double? batteryEfficiency,
  }) => _runOptimization(
    initialSoc: initialSoc,
    targetDate: targetDate,
    temperatureForecast: temperatureForecast,
    temperatureAdjust: temperatureAdjust,
    batteryCapacity: batteryCapacity,
    batteryPower: batteryPower,
    batteryEfficiency: batteryEfficiency,
  );

  static Future<Map<String, dynamic>> getOptimizationConfig() =>
      _getOptimizationConfig();

  static Future<Map<String, dynamic>> simulateScenarios({
    DateTime? targetDate,
    List<Map<String, dynamic>>? scenarios,
  }) => _simulateScenarios(targetDate: targetDate, scenarios: scenarios);

  static Future<Map<String, dynamic>> trainDeepModel({
    required String storagePath,
    String? modelType = 'lstm',
    int? epochs = 50,
    int? batchSize = 32,
    int? windowSize = 24,
    String? targetColumn,
  }) => _trainDeepModel(
    storagePath: storagePath,
    modelType: modelType,
    epochs: epochs,
    batchSize: batchSize,
    windowSize: windowSize,
    targetColumn: targetColumn,
  );

  static Future<Map<String, dynamic>> askRagQuestion({
    required String question,
    String? collectionName,
  }) => _askRagQuestion(question: question, collectionName: collectionName);
}
