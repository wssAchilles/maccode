import 'package:flutter_test/flutter_test.dart';
import 'package:front/models/analysis_result.dart';
import 'package:front/models/optimization_result.dart';
import 'package:front/services/api_client.dart';
import 'package:front/services/data_analysis_gateway.dart';
import 'package:front/services/deep_learning_gateway.dart';
import 'package:front/services/history_gateway.dart';
import 'package:front/services/optimization_gateway.dart';
import 'package:front/services/rag_gateway.dart';

class _FakeApiClient implements ApiClient {
  Map<String, dynamic>? uploadUrlArgs;
  Map<String, dynamic>? uploadFileArgs;
  Map<String, dynamic>? analyzeArgs;
  Map<String, dynamic>? analysisJobArgs;
  Map<String, dynamic>? driftArgs;
  int? historyLimit;
  String? activityType;
  String? activityStatus;
  String? deletedRecordId;
  Map<String, dynamic>? optimizationArgs;
  Map<String, dynamic>? deepLearningArgs;
  Map<String, dynamic>? ragArgs;

  final uploadUrlResult = <String, dynamic>{
    'uploadUrl': 'https://example.com/upload',
    'storagePath': 'uploads/sample.csv',
  };
  final historyResult = <Map<String, dynamic>>[
    {'id': '1'},
  ];
  final deepLearningResult = <String, dynamic>{'success': true};
  final ragResult = <String, dynamic>{'success': true, 'answer': 'ok'};

  @override
  Future<Map<String, dynamic>> getDashboardAssets() async {
    return {
      'inventory': {
        'dataset_assets': 1,
        'model_assets': 1,
        'knowledge_assets': 1,
        'optimization_assets': 1,
      },
      'datasets': const <Map<String, dynamic>>[],
      'models': const <Map<String, dynamic>>[],
      'knowledge_bases': const <Map<String, dynamic>>[],
      'optimizations': const <Map<String, dynamic>>[],
    };
  }

  @override
  Future<Map<String, dynamic>> getUploadUrl({
    required String fileName,
    required String contentType,
  }) async {
    uploadUrlArgs = {'fileName': fileName, 'contentType': contentType};
    return uploadUrlResult;
  }

  @override
  Future<void> uploadFileToGcs({
    required String uploadUrl,
    required List<int> fileData,
    required String contentType,
  }) async {
    uploadFileArgs = {
      'uploadUrl': uploadUrl,
      'fileData': fileData,
      'contentType': contentType,
    };
  }

  @override
  Future<AnalysisResult> analyzeCsv({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  }) async {
    analyzeArgs = {
      'storagePath': storagePath,
      'filename': filename,
      'saveToStorage': saveToStorage,
    };
    return AnalysisResult(
      basicInfo: BasicInfo(
        rows: 1,
        columns: 1,
        columnNames: const ['value'],
        columnTypes: const {'value': 'double'},
      ),
      preview: const [
        {'value': 1.0},
      ],
    );
  }

  @override
  Future<Map<String, dynamic>> createAnalysisJob({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  }) async {
    analysisJobArgs = {
      'storagePath': storagePath,
      'filename': filename,
      'saveToStorage': saveToStorage,
    };
    return {
      'job_id': 'analysis-job-1',
      'type': 'analysis',
      'status': 'queued',
      'progress': 0,
      'requested_by': 'test-user',
      'attempt_count': 0,
      'max_attempts': 1,
      'input': {'storage_path': storagePath},
      'result': const <String, dynamic>{},
      'retryable': false,
      'events': const <Map<String, dynamic>>[],
    };
  }

  @override
  Future<Map<String, dynamic>> detectDataDrift({
    required String referencePath,
    required String currentPath,
    required List<String> features,
  }) async {
    driftArgs = {
      'referencePath': referencePath,
      'currentPath': currentPath,
      'features': features,
    };
    return {
      'drift_results': {
        'overall_status': 'stable',
        'recommendation': 'ok',
        'summary': {'stable': 1, 'warning': 0, 'drift': 0},
        'features': const <String, dynamic>{},
      },
      'report': '# ok',
    };
  }

  @override
  Future<List<Map<String, dynamic>>> getUserHistory({int limit = 20}) async {
    historyLimit = limit;
    return historyResult;
  }

  @override
  Future<List<Map<String, dynamic>>> getAuditActivity({
    String? type,
    String? status,
    int limit = 20,
  }) async {
    historyLimit = limit;
    activityType = type;
    activityStatus = status;
    return const <Map<String, dynamic>>[];
  }

  @override
  Future<void> deleteHistoryRecord(String recordId) async {
    deletedRecordId = recordId;
  }

  @override
  Future<OptimizationResponse> runOptimization({
    double initialSoc = 0.5,
    DateTime? targetDate,
    double? temperatureAdjust,
    double? batteryCapacity,
    double? batteryPower,
  }) async {
    optimizationArgs = {
      'initialSoc': initialSoc,
      'targetDate': targetDate,
      'temperatureAdjust': temperatureAdjust,
      'batteryCapacity': batteryCapacity,
      'batteryPower': batteryPower,
    };
    return OptimizationResponse(success: true);
  }

  @override
  Future<Map<String, dynamic>> trainDeepModel({
    required String storagePath,
    required String modelType,
    required int epochs,
    required int batchSize,
    required int windowSize,
    String? targetColumn,
  }) async {
    deepLearningArgs = {
      'storagePath': storagePath,
      'modelType': modelType,
      'epochs': epochs,
      'batchSize': batchSize,
      'windowSize': windowSize,
      'targetColumn': targetColumn,
    };
    return deepLearningResult;
  }

  @override
  Future<Map<String, dynamic>> askRagQuestion({
    required String question,
    String? collectionName,
  }) async {
    ragArgs = {'question': question, 'collectionName': collectionName};
    return ragResult;
  }
}

void main() {
  group('API gateways', () {
    test(
      'ApiDataAnalysisGateway delegates upload and analysis calls to ApiClient',
      () async {
        final client = _FakeApiClient();
        final gateway = ApiDataAnalysisGateway(apiClient: client);

        final uploadInfo = await gateway.getUploadUrl(
          fileName: 'sample.csv',
          contentType: 'text/csv',
        );
        await gateway.uploadFileToGcs(
          uploadUrl: 'https://example.com/upload',
          fileData: const [1, 2, 3],
          contentType: 'text/csv',
        );
        final result = await gateway.analyzeCsv(
          storagePath: 'uploads/sample.csv',
          filename: 'sample.csv',
          saveToStorage: false,
        );

        expect(uploadInfo['storagePath'], 'uploads/sample.csv');
        expect(client.uploadUrlArgs, {
          'fileName': 'sample.csv',
          'contentType': 'text/csv',
        });
        expect(client.uploadFileArgs?['fileData'], [1, 2, 3]);
        expect(client.analyzeArgs?['saveToStorage'], isFalse);
        expect(result.basicInfo.rows, 1);
      },
    );

    test(
      'ApiHistoryGateway delegates history operations to ApiClient',
      () async {
        final client = _FakeApiClient();
        final gateway = ApiHistoryGateway(apiClient: client);

        final history = await gateway.getUserHistory(limit: 42);
        await gateway.deleteHistoryRecord('record-1');

        expect(history, hasLength(1));
        expect(client.historyLimit, 42);
        expect(client.deletedRecordId, 'record-1');
      },
    );

    test(
      'ApiOptimizationGateway delegates optimization parameters to ApiClient',
      () async {
        final client = _FakeApiClient();
        final gateway = ApiOptimizationGateway(apiClient: client);
        final targetDate = DateTime(2026, 3, 7);

        final result = await gateway.runOptimization(
          initialSoc: 0.6,
          targetDate: targetDate,
          temperatureAdjust: 1.5,
          batteryCapacity: 120,
          batteryPower: 60,
        );

        expect(result.isSuccess, isTrue);
        expect(client.optimizationArgs, {
          'initialSoc': 0.6,
          'targetDate': targetDate,
          'temperatureAdjust': 1.5,
          'batteryCapacity': 120.0,
          'batteryPower': 60.0,
        });
      },
    );

    test(
      'ApiDeepLearningGateway delegates training request to ApiClient',
      () async {
        final client = _FakeApiClient();
        final gateway = ApiDeepLearningGateway(apiClient: client);

        final result = await gateway.trainModel(
          storagePath: 'uploads/train.csv',
          modelType: 'gru',
          epochs: 30,
          batchSize: 16,
          windowSize: 48,
          targetColumn: 'load',
        );

        expect(result['success'], isTrue);
        expect(client.deepLearningArgs, {
          'storagePath': 'uploads/train.csv',
          'modelType': 'gru',
          'epochs': 30,
          'batchSize': 16,
          'windowSize': 48,
          'targetColumn': 'load',
        });
      },
    );

    test('ApiRagGateway delegates question to ApiClient', () async {
      final client = _FakeApiClient();
      final gateway = ApiRagGateway(apiClient: client);

      final result = await gateway.askQuestion(
        question: 'What is the peak load?',
      );

      expect(result['answer'], 'ok');
      expect(client.ragArgs, {
        'question': 'What is the peak load?',
        'collectionName': null,
      });
    });
  });
}
