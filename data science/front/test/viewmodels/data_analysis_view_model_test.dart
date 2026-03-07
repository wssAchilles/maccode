import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/analysis_result.dart';
import 'package:front/models/data_analysis_error.dart';
import 'package:front/services/auth_gateway.dart';
import 'package:front/services/data_analysis_gateway.dart';
import 'package:front/viewmodels/data_analysis_view_model.dart';

class _FakeAuthGateway implements AuthGateway {
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
  bool uploadCalled = false;
  bool analyzeCalled = false;
  bool? lastSaveToStorage;

  @override
  Future<Map<String, dynamic>> getUploadUrl({
    required String fileName,
    required String contentType,
  }) async {
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
  }

  @override
  Future<AnalysisResult> analyzeCsv({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  }) async {
    analyzeCalled = true;
    lastSaveToStorage = saveToStorage;
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
}
