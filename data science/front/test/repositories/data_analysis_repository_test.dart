import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/analysis_result.dart';
import 'package:front/models/data_analysis_error.dart';
import 'package:front/repositories/data_analysis_repository.dart';
import 'package:front/services/api_service_exception.dart';
import 'package:front/services/data_analysis_gateway.dart';

class _FakeDataAnalysisGateway implements DataAnalysisGateway {
  _FakeDataAnalysisGateway({
    this.getUploadUrlHandler,
    this.uploadFileHandler,
    this.analyzeCsvHandler,
  });

  bool uploadCalled = false;
  bool analyzeCalled = false;
  bool? lastSaveToStorage;

  final Future<Map<String, dynamic>> Function({
    required String fileName,
    required String contentType,
  })?
  getUploadUrlHandler;
  final Future<void> Function({
    required String uploadUrl,
    required List<int> fileData,
    required String contentType,
  })?
  uploadFileHandler;
  final Future<AnalysisResult> Function({
    required String storagePath,
    String? filename,
    bool saveToStorage,
  })?
  analyzeCsvHandler;

  @override
  Future<Map<String, dynamic>> getUploadUrl({
    required String fileName,
    required String contentType,
  }) async {
    final handler = getUploadUrlHandler;
    if (handler != null) {
      return handler(fileName: fileName, contentType: contentType);
    }

    return {
      'uploadUrl': 'https://upload.example.com/signed',
      'storagePath': 'uploads/$fileName',
    };
  }

  @override
  Future<void> uploadFileToGcs({
    required String uploadUrl,
    required List<int> fileData,
    required String contentType,
  }) async {
    uploadCalled = true;
    final handler = uploadFileHandler;
    if (handler != null) {
      return handler(
        uploadUrl: uploadUrl,
        fileData: fileData,
        contentType: contentType,
      );
    }
  }

  @override
  Future<AnalysisResult> analyzeCsv({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  }) async {
    analyzeCalled = true;
    lastSaveToStorage = saveToStorage;
    final handler = analyzeCsvHandler;
    if (handler != null) {
      return handler(
        storagePath: storagePath,
        filename: filename,
        saveToStorage: saveToStorage,
      );
    }

    return AnalysisResult(
      basicInfo: BasicInfo(
        rows: 1,
        columns: 1,
        columnNames: const ['value'],
        columnTypes: const {'value': 'int64'},
      ),
      preview: const [
        {'value': 1},
      ],
    );
  }

  @override
  Future<Map<String, dynamic>> createAnalysisJob({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  }) async {
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
}

void main() {
  test(
    'submitCsvAnalysis returns validation error when file bytes are missing',
    () async {
      final repository = GatewayDataAnalysisRepository(
        dataGateway: _FakeDataAnalysisGateway(),
      );

      final result = await repository.submitCsvAnalysis(
        file: PlatformFile(name: 'sample.csv', size: 10),
        saveToStorage: true,
      );

      expect(result.isFailure, isTrue);
      expect(result.error?.type, DataAnalysisErrorType.validation);
      expect(result.error?.message, '文件读取失败，请重新选择文件');
    },
  );

  test('submitCsvAnalysis maps upload timeout to upload failure', () async {
    final gateway = _FakeDataAnalysisGateway(
      uploadFileHandler:
          ({
            required uploadUrl,
            required fileData,
            required contentType,
          }) async {
            throw const ApiServiceException(
              'request timed out',
              kind: ApiServiceErrorKind.timeout,
            );
          },
    );
    final repository = GatewayDataAnalysisRepository(dataGateway: gateway);

    final result = await repository.submitCsvAnalysis(
      file: PlatformFile(
        name: 'sample.csv',
        size: 2,
        bytes: Uint8List.fromList([1, 2]),
      ),
      saveToStorage: true,
    );

    expect(result.isFailure, isTrue);
    expect(result.error?.type, DataAnalysisErrorType.upload);
    expect(result.error?.message, '文件上传超时，请检查网络后重试');
    expect(gateway.uploadCalled, isTrue);
    expect(gateway.analyzeCalled, isFalse);
  });

  test(
    'submitCsvAnalysis maps unauthenticated upload-url failure to auth failure',
    () async {
      final gateway = _FakeDataAnalysisGateway(
        getUploadUrlHandler: ({required fileName, required contentType}) async {
          throw const ApiServiceException(
            'Unauthorized',
            kind: ApiServiceErrorKind.unauthenticated,
          );
        },
      );
      final repository = GatewayDataAnalysisRepository(dataGateway: gateway);

      final result = await repository.submitCsvAnalysis(
        file: PlatformFile(
          name: 'sample.csv',
          size: 2,
          bytes: Uint8List.fromList([1, 2]),
        ),
        saveToStorage: true,
      );

      expect(result.isFailure, isTrue);
      expect(result.error?.type, DataAnalysisErrorType.auth);
      expect(result.error?.message, '登录状态已失效，请重新登录后再试');
      expect(gateway.uploadCalled, isFalse);
      expect(gateway.analyzeCalled, isFalse);
    },
  );

  test(
    'submitCsvAnalysis maps analysis bad response to analysis failure',
    () async {
      final gateway = _FakeDataAnalysisGateway(
        analyzeCsvHandler:
            ({
              required storagePath,
              String? filename,
              bool saveToStorage = true,
            }) async {
              throw const ApiServiceException(
                'Analysis failed: 缺少 analysis_result',
                kind: ApiServiceErrorKind.badResponse,
              );
            },
      );
      final repository = GatewayDataAnalysisRepository(dataGateway: gateway);

      final result = await repository.submitCsvAnalysis(
        file: PlatformFile(
          name: 'sample.csv',
          size: 2,
          bytes: Uint8List.fromList([1, 2]),
        ),
        saveToStorage: true,
      );

      expect(result.isFailure, isTrue);
      expect(result.error?.type, DataAnalysisErrorType.analysis);
      expect(result.error?.message, '分析结果格式异常，请稍后重试');
      expect(gateway.uploadCalled, isTrue);
      expect(gateway.analyzeCalled, isTrue);
    },
  );

  test(
    'submitCsvAnalysis returns success result when gateway flow succeeds',
    () async {
      final gateway = _FakeDataAnalysisGateway();
      final repository = GatewayDataAnalysisRepository(dataGateway: gateway);

      final result = await repository.submitCsvAnalysis(
        file: PlatformFile(
          name: 'sample.csv',
          size: 2,
          bytes: Uint8List.fromList([1, 2]),
        ),
        saveToStorage: false,
      );

      expect(result.isSuccess, isTrue);
      expect(result.analysisResult, isNotNull);
      expect(result.error, isNull);
      expect(gateway.uploadCalled, isTrue);
      expect(gateway.analyzeCalled, isTrue);
      expect(gateway.lastSaveToStorage, isFalse);
    },
  );
}
