import 'dart:typed_data';

import 'package:file_picker/file_picker.dart';
import 'package:firebase_auth/firebase_auth.dart';
import 'package:flutter/material.dart';
import 'package:flutter_test/flutter_test.dart';

import 'package:front/models/analysis_result.dart';
import 'package:front/screens/data_analysis_screen.dart';
import 'package:front/services/api_service_exception.dart';
import 'package:front/services/auth_gateway.dart';
import 'package:front/services/data_analysis_gateway.dart';
import 'package:front/viewmodels/data_analysis_view_model.dart';

class _FakeUser extends Fake implements User {
  _FakeUser({
    required this.email,
    this.displayName,
    this.emailVerified = false,
  });

  @override
  final String? email;

  @override
  final String? displayName;

  @override
  final bool emailVerified;

  @override
  String get uid => 'user-12345678';

  @override
  String? get photoURL => null;
}

class _FakeUserCredential extends Fake implements UserCredential {
  _FakeUserCredential(this._user);

  final User _user;

  @override
  User? get user => _user;
}

class _FakeAuthGateway implements AuthGateway {
  _FakeAuthGateway({this.currentUserValue, this.signInWithEmailHandler});

  final User? currentUserValue;
  final Future<UserCredential> Function({
    required String email,
    required String password,
  })?
  signInWithEmailHandler;

  @override
  User? get currentUser => currentUserValue;

  @override
  Stream<User?> get authStateChanges => const Stream<User?>.empty();

  @override
  Future<UserCredential> registerWithEmail({
    required String email,
    required String password,
  }) => throw UnimplementedError();

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
  Future<UserCredential> signInWithGoogle() => throw UnimplementedError();

  @override
  Future<void> signOut() async {}
}

class _FakeDataAnalysisGateway implements DataAnalysisGateway {
  _FakeDataAnalysisGateway({this.analyzeCsvHandler});

  final Future<AnalysisResult> Function({
    required String storagePath,
    String? filename,
    bool saveToStorage,
  })?
  analyzeCsvHandler;

  @override
  Future<AnalysisResult> analyzeCsv({
    required String storagePath,
    String? filename,
    bool saveToStorage = true,
  }) async {
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
  }) async {}

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

  @override
  Future<Map<String, dynamic>> detectDataDrift({
    required String referencePath,
    required String currentPath,
    required List<String> features,
  }) async {
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
}

void main() {
  testWidgets('DataAnalysisScreen shows success snackbar after email sign-in', (
    WidgetTester tester,
  ) async {
    final user = _FakeUser(
      email: 'user@example.com',
      displayName: '测试用户',
      emailVerified: true,
    );
    final viewModel = DataAnalysisViewModel(
      authGateway: _FakeAuthGateway(
        signInWithEmailHandler: ({required email, required password}) async {
          return _FakeUserCredential(user);
        },
      ),
      dataGateway: _FakeDataAnalysisGateway(),
    );
    addTearDown(viewModel.dispose);

    await tester.pumpWidget(
      MaterialApp(home: DataAnalysisScreen(viewModel: viewModel)),
    );

    await tester.enterText(
      find.byType(TextFormField).at(0),
      'user@example.com',
    );
    await tester.enterText(find.byType(TextFormField).at(1), 'secret123');
    final loginButton = find.widgetWithText(ElevatedButton, '登录');
    tester.widget<ElevatedButton>(loginButton).onPressed!.call();
    await tester.pumpAndSettle();

    expect(find.text('欢迎回来, user@example.com!'), findsOneWidget);
    expect(find.text('测试用户'), findsOneWidget);
    expect(find.text('已登录'), findsOneWidget);
  });

  testWidgets(
    'DataAnalysisScreen shows snackbar and banner on analysis failure',
    (WidgetTester tester) async {
      await tester.binding.setSurfaceSize(const Size(1200, 1600));
      addTearDown(() => tester.binding.setSurfaceSize(null));

      final viewModel = DataAnalysisViewModel(
        authGateway: _FakeAuthGateway(
          currentUserValue: _FakeUser(
            email: 'user@example.com',
            displayName: '测试用户',
            emailVerified: true,
          ),
        ),
        dataGateway: _FakeDataAnalysisGateway(
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
        ),
      );
      addTearDown(viewModel.dispose);
      viewModel.setPickedFileForTesting(
        PlatformFile(
          name: 'sample.csv',
          size: 2,
          bytes: Uint8List.fromList([1, 2]),
        ),
      );

      await tester.pumpWidget(
        MaterialApp(home: DataAnalysisScreen(viewModel: viewModel)),
      );

      final startButton = find.byKey(const ValueKey('analysis-start-button'));
      tester.widget<InkWell>(startButton).onTap!.call();
      await tester.pumpAndSettle();

      expect(find.text('分析结果格式异常，请稍后重试'), findsAtLeastNWidgets(1));
      expect(find.byType(SnackBar), findsOneWidget);
    },
  );
}
