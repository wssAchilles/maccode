import 'dart:typed_data';
import 'dart:async';

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/analysis_result.dart';
import 'package:front/models/auth_failure.dart';
import 'package:front/models/data_analysis_error.dart';
import 'package:front/services/api_service_exception.dart';
import 'package:front/services/auth_gateway.dart';
import 'package:front/services/data_analysis_gateway.dart';
import 'package:front/viewmodels/data_analysis_view_model.dart';

class _FakeAuthGateway implements AuthGateway {
  _FakeAuthGateway({
    this.signInWithGoogleHandler,
    this.signInWithEmailHandler,
    this.registerWithEmailHandler,
  });

  final Future<UserCredential> Function()? signInWithGoogleHandler;
  final Future<UserCredential> Function({
    required String email,
    required String password,
  })?
  signInWithEmailHandler;
  final Future<UserCredential> Function({
    required String email,
    required String password,
  })?
  registerWithEmailHandler;

  @override
  User? get currentUser => null;

  @override
  Stream<User?> get authStateChanges => Stream<User?>.value(null);

  @override
  Future<void> signOut() async {}

  @override
  Future<UserCredential> registerWithEmail({
    required String email,
    required String password,
  }) async {
    final handler = registerWithEmailHandler;
    if (handler == null) {
      throw UnimplementedError();
    }
    return handler(email: email, password: password);
  }

  @override
  Future<UserCredential> signInWithEmail({
    required String email,
    required String password,
  }) async {
    final handler = signInWithEmailHandler;
    if (handler == null) {
      throw UnimplementedError();
    }
    return handler(email: email, password: password);
  }

  @override
  Future<UserCredential> signInWithGoogle() async {
    final handler = signInWithGoogleHandler;
    if (handler == null) {
      throw UnimplementedError();
    }
    return handler();
  }
}

class _StreamingAuthGateway implements AuthGateway {
  _StreamingAuthGateway(this._controller);

  final StreamController<User?> _controller;

  @override
  User? get currentUser => null;

  @override
  Stream<User?> get authStateChanges => _controller.stream;

  @override
  Future<void> signOut() async {}

  @override
  Future<UserCredential> registerWithEmail({
    required String email,
    required String password,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<UserCredential> signInWithEmail({
    required String email,
    required String password,
  }) async {
    throw UnimplementedError();
  }

  @override
  Future<UserCredential> signInWithGoogle() async {
    throw UnimplementedError();
  }
}

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
  test('toggleAuthMode switches between login and register', () {
    final viewModel = DataAnalysisViewModel(authGateway: _FakeAuthGateway());

    expect(viewModel.authMode, 'login');

    viewModel.toggleAuthMode();
    expect(viewModel.authMode, 'register');

    viewModel.toggleAuthMode();
    expect(viewModel.authMode, 'login');

    viewModel.dispose();
  });

  test('startAnalysis returns false with null file bytes', () async {
    final gateway = _FakeDataAnalysisGateway();
    final viewModel = DataAnalysisViewModel(
      authGateway: _FakeAuthGateway(),
      dataGateway: gateway,
      isAuthenticated: () => true,
    );

    viewModel.setPickedFileForTesting(
      PlatformFile(name: 'sample.csv', size: 10),
    );

    final success = await viewModel.startAnalysis();

    expect(success, isFalse);
    expect(viewModel.errorMessage, contains('文件读取失败'));
    expect(viewModel.error?.type, DataAnalysisErrorType.validation);
    expect(gateway.uploadCalled, isFalse);
    expect(gateway.analyzeCalled, isFalse);

    viewModel.dispose();
  });

  test('startAnalysis uses saveToStorage=true by default', () async {
    final gateway = _FakeDataAnalysisGateway();
    final viewModel = DataAnalysisViewModel(
      authGateway: _FakeAuthGateway(),
      dataGateway: gateway,
      isAuthenticated: () => true,
    );

    viewModel.setPickedFileForTesting(
      PlatformFile(
        name: 'sample.csv',
        size: 2,
        bytes: Uint8List.fromList([1, 2]),
      ),
    );

    final success = await viewModel.startAnalysis();

    expect(success, isTrue);
    expect(viewModel.error, isNull);
    expect(gateway.uploadCalled, isTrue);
    expect(gateway.analyzeCalled, isTrue);
    expect(gateway.lastSaveToStorage, isTrue);
    expect(viewModel.analysisResult, isNotNull);

    viewModel.dispose();
  });

  test('startAnalysis passes saveToStorage=false when disabled', () async {
    final gateway = _FakeDataAnalysisGateway();
    final viewModel = DataAnalysisViewModel(
      authGateway: _FakeAuthGateway(),
      dataGateway: gateway,
      isAuthenticated: () => true,
    );

    viewModel.setSaveToStorage(false);
    viewModel.setPickedFileForTesting(
      PlatformFile(
        name: 'sample.csv',
        size: 2,
        bytes: Uint8List.fromList([1, 2]),
      ),
    );

    final success = await viewModel.startAnalysis();

    expect(success, isTrue);
    expect(gateway.lastSaveToStorage, isFalse);

    viewModel.dispose();
  });

  test(
    'startAnalysis maps unauthenticated upload-url failure to auth error',
    () async {
      final gateway = _FakeDataAnalysisGateway(
        getUploadUrlHandler: ({required fileName, required contentType}) async {
          throw const ApiServiceException(
            'Unauthorized',
            kind: ApiServiceErrorKind.unauthenticated,
          );
        },
      );
      final viewModel = DataAnalysisViewModel(
        authGateway: _FakeAuthGateway(),
        dataGateway: gateway,
        isAuthenticated: () => true,
      );

      viewModel.setPickedFileForTesting(
        PlatformFile(
          name: 'sample.csv',
          size: 2,
          bytes: Uint8List.fromList([1, 2]),
        ),
      );

      final success = await viewModel.startAnalysis();

      expect(success, isFalse);
      expect(viewModel.error?.type, DataAnalysisErrorType.auth);
      expect(viewModel.errorMessage, '登录状态已失效，请重新登录后再试');
      expect(gateway.uploadCalled, isFalse);
      expect(gateway.analyzeCalled, isFalse);

      viewModel.dispose();
    },
  );

  test('startAnalysis maps upload timeout to upload error', () async {
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
    final viewModel = DataAnalysisViewModel(
      authGateway: _FakeAuthGateway(),
      dataGateway: gateway,
      isAuthenticated: () => true,
    );

    viewModel.setPickedFileForTesting(
      PlatformFile(
        name: 'sample.csv',
        size: 2,
        bytes: Uint8List.fromList([1, 2]),
      ),
    );

    final success = await viewModel.startAnalysis();

    expect(success, isFalse);
    expect(viewModel.error?.type, DataAnalysisErrorType.upload);
    expect(viewModel.errorMessage, '文件上传超时，请检查网络后重试');
    expect(gateway.uploadCalled, isTrue);
    expect(gateway.analyzeCalled, isFalse);

    viewModel.dispose();
  });

  test('startAnalysis maps analysis bad response to analysis error', () async {
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
    final viewModel = DataAnalysisViewModel(
      authGateway: _FakeAuthGateway(),
      dataGateway: gateway,
      isAuthenticated: () => true,
    );

    viewModel.setPickedFileForTesting(
      PlatformFile(
        name: 'sample.csv',
        size: 2,
        bytes: Uint8List.fromList([1, 2]),
      ),
    );

    final success = await viewModel.startAnalysis();

    expect(success, isFalse);
    expect(viewModel.error?.type, DataAnalysisErrorType.analysis);
    expect(viewModel.errorMessage, '分析结果格式异常，请稍后重试');
    expect(gateway.uploadCalled, isTrue);
    expect(gateway.analyzeCalled, isTrue);

    viewModel.dispose();
  });

  test('initialize is idempotent and subscribes to auth state once', () async {
    final controller = StreamController<User?>.broadcast();
    final viewModel = DataAnalysisViewModel(
      authGateway: _StreamingAuthGateway(controller),
    );
    var notifications = 0;

    viewModel.addListener(() => notifications += 1);

    viewModel.initialize();
    viewModel.initialize();

    controller.add(null);
    await Future<void>.delayed(Duration.zero);

    expect(notifications, 2);

    await controller.close();
    viewModel.dispose();
  });

  test(
    'signInWithEmail maps AuthFailureException to stable auth error',
    () async {
      final viewModel = DataAnalysisViewModel(
        authGateway: _FakeAuthGateway(
          signInWithEmailHandler: ({required email, required password}) async {
            throw const AuthFailureException(
              AuthFailure(code: 'invalid-credential', message: '用户不存在或密码错误'),
            );
          },
        ),
      );

      final user = await viewModel.signInWithEmail(
        email: 'user@example.com',
        password: 'secret123',
      );

      expect(user, isNull);
      expect(viewModel.error?.type, DataAnalysisErrorType.auth);
      expect(viewModel.errorMessage, '登录失败: 用户不存在或密码错误');

      viewModel.dispose();
    },
  );

  test(
    'registerWithEmail maps AuthFailureException to stable auth error',
    () async {
      final viewModel = DataAnalysisViewModel(
        authGateway: _FakeAuthGateway(
          registerWithEmailHandler:
              ({required email, required password}) async {
                throw const AuthFailureException(
                  AuthFailure(code: 'weak-password', message: '密码强度太弱'),
                );
              },
        ),
      );

      final user = await viewModel.registerWithEmail(
        email: 'user@example.com',
        password: '123456',
      );

      expect(user, isNull);
      expect(viewModel.error?.type, DataAnalysisErrorType.auth);
      expect(viewModel.errorMessage, '注册失败: 密码强度太弱');

      viewModel.dispose();
    },
  );

  test('signInWithGoogle ignores cancelled auth failure', () async {
    final viewModel = DataAnalysisViewModel(
      authGateway: _FakeAuthGateway(
        signInWithGoogleHandler: () async {
          throw const AuthFailureException(
            AuthFailure(code: 'cancelled', message: '登录已取消'),
          );
        },
      ),
    );

    final user = await viewModel.signInWithGoogle();

    expect(user, isNull);
    expect(viewModel.error, isNull);

    viewModel.dispose();
  });
}
